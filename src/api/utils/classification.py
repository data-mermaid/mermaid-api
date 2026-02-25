import datetime
import hashlib
import math
import os
from enum import Enum
from io import BytesIO
from operator import itemgetter
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import Any, Dict, Optional, Tuple

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from django.conf import settings
from django.contrib.gis.geos import Point as GEOSPoint
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef
from django.db.models.fields.files import ImageFieldFile
from django.utils import timezone
from exif import Image as ExifImage
from PIL import Image as PILImage
from PIL.ExifTags import TAGS
from plum.exceptions import UnpackError
from spacer.extractors import EfficientNetExtractor
from spacer.messages import ClassifyFeaturesMsg, DataLocation, ExtractFeaturesMsg
from spacer.tasks import classify_features, extract_features

from ..models import (
    Annotation,
    ClassificationStatus,
    Classifier,
    Image,
    ObsBenthicPhotoQuadrat,
    Point,
    Profile,
    Project,
    Region,
    Site,
)
from ..models.classification import get_image_storage_config
from .q import submit_image_job
from .s3 import download_directory, upload_file

CLASSIFIER_CONFIG_S3_PATH = "classifier"
CLASSIFIER_CONFIG_LOCAL_CACHE_DIR = settings.SPACER.get("EXTRACTORS_CACHE_DIR")
assert CLASSIFIER_CONFIG_LOCAL_CACHE_DIR is not None
CLASSIFIER_FILE_NAME = "classifier.pkl"
WEIGHTS_FILE_NAME = "efficientnet_weights.pt"
ANNOTATIONS_PARQUET_FILE_NAME = "mermaid_confirmed_annotations.parquet"


def _get_file_for_reading(image_fieldfile: ImageFieldFile):
    """
    Return a readable file object from an ImageFieldFile, regardless of whether
    it's already open, in-memory, or needs reopening from storage.
    """
    try:
        file_obj = image_fieldfile.file
        file_obj.seek(0)
        return file_obj
    except ValueError:
        # File is closed and can't be reopened in-memory — fetch from storage
        image_fieldfile.open("rb")
        return image_fieldfile.file


def check_if_valid_image(instance):
    file_obj = _get_file_for_reading(instance.image)

    try:
        with PILImage.open(file_obj) as img:
            img.verify()
            w, h = img.size
            if settings.MAX_IMAGE_PIXELS < w * h:
                raise ValueError(f"Maximum number of pixels is {settings.MAX_IMAGE_PIXELS}.")
        return
    except (AttributeError, TypeError, IOError, SyntaxError) as _:
        raise ValueError("Invalid image.")


def create_image_name(image: Image) -> str:
    name = str(image.id)
    image_name = image.image.name
    image_ext = os.path.splitext(image_name)[1]

    return f"{name}{image_ext}"


def create_image_checksum(image: ImageFieldFile) -> str:
    if not image.closed:
        image.close()
    image.open("rb")
    image.seek(0)

    file_hash = hashlib.sha256()
    for chunk in image.chunks(chunk_size=8192):
        file_hash.update(chunk)

    image.close()
    return file_hash.hexdigest()


def create_thumbnail(image_instance: Image) -> ContentFile:
    size = (500, 500)

    with image_instance.image.open("rb") as f:
        img = PILImage.open(f)
        img.load()

    img.thumbnail(size, PILImage.Resampling.LANCZOS)

    base, ext = os.path.splitext(image_instance.name)
    thumb_name = f"{base}_thumbnail{ext}"

    thumb_io = BytesIO()
    try:
        img.save(thumb_io, img.format)
    except IOError as io_err:
        print(f"Cannot create thumbnail for [{image_instance.pk}]: {io_err}")
        raise

    return ContentFile(thumb_io.getvalue(), name=thumb_name)


def convert_to_utc(timestamp_str: str) -> datetime:
    local_time = datetime.fromisoformat(timestamp_str)
    return local_time.astimezone(datetime.timezone.utc)


def extract_datetime_stamp(exif_details: Dict[str, Any]) -> Optional[datetime.datetime]:
    date_stamp = exif_details.get("gps_datestamp")  # str, 2024:04:06
    time_stamp = exif_details.get("gps_timestamp")  # tuple

    if date_stamp and time_stamp:
        date_stamp = map(int, date_stamp.split(":"))
        time_stamp = map(int, time_stamp)
        return datetime.datetime(*date_stamp, *time_stamp, tzinfo=datetime.timezone.utc)

    date_time_str = exif_details.get("datetime_original")
    offset_time = exif_details.get("offset_time")

    if not date_stamp or not date_time_str or offset_time is None:
        return None

    dt = datetime.datetime.strptime(date_time_str, "%Y:%m:%d %H:%M:%S")
    offset = datetime.timedelta(hours=offset_time)
    local_tz = datetime.timezone(offset)
    dt_local = dt.replace(tzinfo=local_tz)

    return dt_local.astimezone(datetime.timezone.utc)


def extract_location(exif_details: Dict[str, Any]) -> Optional[GEOSPoint]:
    latitude_ref = exif_details.get("gps_latitude_ref")  # N or S
    latitude_dms = exif_details.get("gps_latitude")  # tuple (DMS)
    longitude_ref = exif_details.get("gps_longitude_ref")  # E or W
    longitude_dms = exif_details.get("gps_longitude")  # tuple (DMS)

    if (
        not all([latitude_ref, latitude_dms, longitude_ref, longitude_dms])
        or len(latitude_dms) < 3
        or len(longitude_dms) < 3
    ):
        return None

    latitude = latitude_dms[0] + latitude_dms[1] / 60 + latitude_dms[2] / 3600
    longitude = longitude_dms[0] + longitude_dms[1] / 60 + longitude_dms[2] / 3600

    latitude *= -1 if latitude_ref == "S" else 1
    longitude *= -1 if longitude_ref == "W" else 1

    return GEOSPoint(longitude, latitude)


def save_normalized_imagefile(instance: Image):
    file_obj = _get_file_for_reading(instance.image)

    with PILImage.open(file_obj) as image_file:
        image_format = image_file.format
        try:
            for orientation in TAGS.keys():
                if TAGS[orientation] == "Orientation":
                    break

            exif = dict(image_file._getexif().items())

            if exif[orientation] == 3:
                image_file = image_file.rotate(180, expand=True)
            elif exif[orientation] == 6:
                image_file = image_file.rotate(270, expand=True)
            elif exif[orientation] == 8:
                image_file = image_file.rotate(90, expand=True)
        except (AttributeError, KeyError, IndexError) as _:
            pass

        # Saving the orientated image back to the image record
        # strips out the EXIF data, which is intentional.
        img_content = BytesIO()
        image_file.save(img_content, format=image_format)

        instance.image = ContentFile(img_content.getvalue(), name=instance.image.name)


def store_exif(instance: Image) -> Dict[str, Any]:
    file_obj = _get_file_for_reading(instance.image)

    with PILImage.open(file_obj) as img:
        try:
            exif_image = ExifImage(img.read())
            if exif_image.has_exif is False:
                return
        except UnpackError:
            return

    exif_details = {}
    for k, v in exif_image.get_all().items():
        if isinstance(v, Enum):
            v = v.name
        elif isinstance(v, (int, float, tuple, list)):
            ...
        else:
            v = str(v).strip().replace("\u0000", "")

        exif_details[k] = v

    instance.data = instance.data or {}
    instance.data["exif"] = exif_details
    instance.location = extract_location(exif_details)
    instance.photo_timestamp = extract_datetime_stamp(exif_details)


def create_classification_status(image, status, message=None):
    try:
        with transaction.atomic():
            # Lock and verify image exists
            if not Image.objects.filter(id=image.pk).select_for_update().exists():
                print(f"Image {image.pk} was deleted, skipping status update")
                return
            ClassificationStatus.objects.create(image=image, status=status, message=message)
    except IntegrityError:
        # Image was deleted after check but before create
        print(f"Image {image.pk} was deleted during status update")
    except Exception as err:
        print(f"Writing classification status Image {image.pk}, status: {status}: {err}")


def generate_points(image: Image, num_points: int, margin: Tuple[int, int] = (0, 0)):
    assert len(margin) == 2

    if image.original_image_height and image.original_image_width:
        h = image.original_image_height
        w = image.original_image_width
    else:
        h = image.image.height
        w = image.image.width

    points_per_side = math.ceil(math.sqrt(num_points)) + 1
    shift_y = (h - 2 * margin[0]) / points_per_side
    shift_x = (w - 2 * margin[1]) / points_per_side

    points_per_side -= 1

    start_x = margin[1] + shift_x
    start_y = margin[0] + shift_y
    coords = []
    for y in range(points_per_side):
        cur_y = int(start_y + (shift_y * y))
        for x in range(points_per_side):
            coords.append((cur_y, int(start_x + (shift_x * x))))

    return coords


def _fetch_and_cache_classifier_config(classifier: Classifier):
    cls_version = classifier.version

    classifier_s3_dir = f"{CLASSIFIER_CONFIG_S3_PATH}/{cls_version}"
    classifier_local_dir = f"{CLASSIFIER_CONFIG_LOCAL_CACHE_DIR}/{cls_version}"
    download_directory(settings.AWS_CONFIG_BUCKET, classifier_s3_dir, classifier_local_dir)


def _get_classifier_and_weights(
    classifier: Optional[Classifier] = None
) -> Tuple[DataLocation, DataLocation]:
    # TODO: Handle if classifier configs don't exist for classifier instance.
    if not classifier:
        classifier = Classifier.latest()

    cls_version = classifier.version
    classifier_dir = f"{CLASSIFIER_CONFIG_LOCAL_CACHE_DIR}/{cls_version}"
    classifier_path = f"{classifier_dir}/{CLASSIFIER_FILE_NAME}"
    weights_path = f"{classifier_dir}/{WEIGHTS_FILE_NAME}"

    if not Path(classifier_path).exists() or not Path(weights_path).exists():
        _fetch_and_cache_classifier_config(classifier)

    return (
        DataLocation("filesystem", classifier_path),
        DataLocation("filesystem", weights_path),
        classifier,
    )


def _get_image_location(image: Image):
    if settings.ENVIRONMENT == "local":
        return DataLocation("filesystem", image.image.path)
    else:
        config = get_image_storage_config(image.image_bucket)
        return DataLocation(
            storage_type="s3",
            key=f"{config['s3_path']}{image.image.name}",
            bucket_name=config["bucket"],
        )


@transaction.atomic
def _write_classification_results(image, score_sets, label_ids, classifer_record, profile=None):
    _annotations = []
    _points = []
    created_on = timezone.now()

    for row, col, scores in score_sets:
        _label_ids = label_ids[:]
        point = Point(
            row=row,
            column=col,
            image=image,
            created_on=created_on,
            updated_on=created_on,
            created_by=profile,
            updated_by=profile,
        )
        _points.append(point)
        top_predictions = sorted(zip(_label_ids, scores), key=itemgetter(1), reverse=True)
        for label, score in top_predictions[0:3]:
            ba_id, gf_id = (label.split("::", 1) + [None])[:2]
            if score >= settings.CLASSIFIED_THRESHOLD and ba_id is not None:
                _annotations.append(
                    Annotation(
                        point=point,
                        classifier=classifer_record,
                        benthic_attribute_id=ba_id,
                        growth_form_id=gf_id,
                        score=score * 100,
                        is_confirmed=score >= settings.AUTOCONFIRM_THRESHOLD,
                        created_on=created_on,
                        updated_on=created_on,
                        created_by=profile,
                        updated_by=profile,
                        is_machine_created=True,
                    )
                )

    Point.objects.bulk_create(_points)
    Annotation.objects.bulk_create(_annotations)


def _classify_image(image_record_id, profile_id=None):
    profile = Profile.objects.get_or_none(id=profile_id) if profile_id else None

    image = Image.objects.get_or_none(id=image_record_id)
    if not image:
        return

    create_classification_status(image, ClassificationStatus.RUNNING)

    try:
        tmp_dir = TemporaryDirectory()
        tmp_feat_vector_file_path = Path(tmp_dir.name, f"{image.id}.featurevector")
        feature_location = DataLocation("filesystem", tmp_feat_vector_file_path)

        data_location = _get_image_location(image)
        classifier, weights, classifer_record = _get_classifier_and_weights()
        points = generate_points(image, 25)

        extract_features_msg = ExtractFeaturesMsg(
            job_token=image_record_id,
            extractor=EfficientNetExtractor(
                data_locations=dict(
                    weights=weights,
                ),
            ),
            rowcols=points,
            image_loc=data_location,
            feature_loc=feature_location,
        )
        classify_features_msg = ClassifyFeaturesMsg(
            job_token=extract_features_msg.job_token,
            feature_loc=extract_features_msg.feature_loc,
            classifier_loc=classifier,
        )
        _ = extract_features(extract_features_msg)
        response_message = classify_features(classify_features_msg)
        label_ids = response_message.classes
        score_sets = response_message.scores
        _write_classification_results(image, score_sets, label_ids, classifer_record, profile)

        with open(tmp_feat_vector_file_path, "rb") as tmp_feat_vector_file:
            image.feature_vector_file.save(
                f"{image.id}_featurevector", tmp_feat_vector_file, save=True
            )

        create_classification_status(image, ClassificationStatus.COMPLETED)
    except Exception as err:
        print(err)
        create_classification_status(image, ClassificationStatus.FAILED, str(err))
    finally:
        if Path(tmp_feat_vector_file_path).exists():
            os.unlink(tmp_feat_vector_file_path)


def classify_image_job(image_record_id, profile_id=None):
    return submit_image_job(0, True, _classify_image, image_record_id=image_record_id)


def classify_image(image_record_id, profile_id=None):
    _classify_image(image_record_id)


def chunked_queryset_dataframe(qs, chunk_size=10000):
    buffer = []
    for obj in qs.iterator(chunk_size=chunk_size):
        buffer.append(obj)
        if len(buffer) >= chunk_size:
            yield pd.DataFrame(buffer)
            buffer.clear()
    if buffer:
        yield pd.DataFrame(buffer)


def get_site_regions(site_ids):
    sites = Site.objects.filter(id__in=site_ids).exclude(location__isnull=True)

    site_to_region = {}
    for site in sites:
        region = Region.objects.filter(geom__intersects=site.location).first()
        if region:
            site_to_region[str(site.id)] = {
                "region_id": str(region.id),
                "region_name": region.name,
            }
        else:
            site_to_region[str(site.id)] = {
                "region_id": None,
                "region_name": None,
            }

    return site_to_region


def _process_annotations_df(df):
    df.rename(
        columns={
            "point__image_id": "image_id",
            "point__row": "row",
            "point__column": "col",
            "benthic_attribute__name": "benthic_attribute_name",
            "growth_form__name": "growth_form_name",
        },
        inplace=True,
    )

    uuid_cols = ["id", "image_id", "point_id", "benthic_attribute_id", "growth_form_id"]
    for col in uuid_cols:
        if col in df.columns:
            df[col] = df[col].astype(str)

    image_ids = df["image_id"].unique().tolist()
    images = Image.objects.filter(id__in=image_ids)
    image_to_site = {str(image.id): str(image.site.id) for image in images if image.site}

    site_to_region = get_site_regions(image_to_site.values())

    def get_region_info(image_id):
        site_id = image_to_site.get(image_id)
        region = site_to_region.get(site_id, {"region_id": None, "region_name": None})
        return pd.Series([region["region_id"], region["region_name"]])

    df[["region_id", "region_name"]] = df["image_id"].apply(get_region_info).apply(pd.Series)

    return df


def export_annotations_to_parquet_streaming(output_path, chunk_size=10000):
    valid_image_ids = (
        Image.objects.annotate(
            has_valid_obs=Exists(
                ObsBenthicPhotoQuadrat.objects.filter(
                    image=OuterRef("pk"),
                    **{f"{ObsBenthicPhotoQuadrat.project_lookup}__status__gt": Project.TEST},
                )
            )
        )
        .filter(has_valid_obs=True)
        .values_list("id", flat=True)
    )

    qs = (
        Annotation.objects.select_related(
            "point", "point__image", "benthic_attribute", "growth_form"
        )
        .filter(
            is_confirmed=True,
            point__image_id__in=valid_image_ids,
        )
        .order_by("point__image__id", "point__row", "point__column")
        .values(
            "id",
            "point__image_id",
            "point_id",
            "point__row",
            "point__column",
            "benthic_attribute_id",
            "benthic_attribute__name",
            "growth_form_id",
            "growth_form__name",
            "updated_on",
        )
    )
    if not qs.exists():
        print("No confirmed annotations found. Nothing to export.")
        return None

    writer = None
    total = 0

    try:
        for df in chunked_queryset_dataframe(qs, chunk_size):
            df = _process_annotations_df(df)
            table = pa.Table.from_pandas(df)
            if writer is None:
                writer = pq.ParquetWriter(output_path, table.schema)
            writer.write_table(table)
            total += len(df)
    finally:
        if writer:
            writer.close()

    print(f"Exported {total} annotations to {output_path}")
    return Path(output_path)


def export_annotations_parquet(chunk_size=10000):
    with NamedTemporaryFile(mode="wb", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        output = export_annotations_to_parquet_streaming(tmp_path, chunk_size)

        if output and output.exists():
            upload_file(
                settings.IMAGE_PROCESSING_BUCKET,
                output,
                f"{settings.IMAGE_S3_PATH}{ANNOTATIONS_PARQUET_FILE_NAME}",
                content_type="application/x-parquet",
                aws_access_key_id=settings.IMAGE_BUCKET_AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.IMAGE_BUCKET_AWS_SECRET_ACCESS_KEY,
            )

            print(
                f"Uploaded to {settings.IMAGE_PROCESSING_BUCKET}: {ANNOTATIONS_PARQUET_FILE_NAME}"
            )

    finally:
        if tmp_path.exists():
            tmp_path.unlink()
