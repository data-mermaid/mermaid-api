import datetime
import hashlib
import math
import os
from enum import Enum
from io import BytesIO
from operator import itemgetter
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import pytz
from django.conf import settings
from django.contrib.gis.geos import Point as GEOSPoint
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models.fields.files import ImageFieldFile
from django.utils import timezone
from exif import Image as ExifImage
from PIL import Image as PILImage
from PIL.ExifTags import TAGS
from spacer.extract_features import EfficientNetExtractor
from spacer.messages import ClassifyFeaturesMsg, DataLocation, ExtractFeaturesMsg
from spacer.tasks import classify_features, extract_features

from ..models import (
    Annotation,
    ClassificationStatus,
    Classifier,
    Image,
    Label,
    Point,
    Profile,
)
from .encryption import encrypt_string
from .q import submit_image_job
from .s3 import download_directory

CLASSIFIER_CONFIG_S3_PATH = "classifier"
CLASSIFIER_CONFIG_LOCAL_CACHE_DIR = "/tmp/classifier"
CLASSIFIER_FILE_NAME = "classifier.pkl"
WEIGHTS_FILE_NAME = "efficientnet_weights.pt"


def create_unique_image_name(image: Image) -> str:
    site = image.site
    if not site:
        raise ValueError(f"No site is related to image {image.id}")

    site_id = str(site.id)
    uid_str = f"{site_id}-{image.id}"

    name = encrypt_string(uid_str)

    image_name = image.image.name
    image_ext = os.path.splitext(image_name)[1]

    return f"{name}{image_ext}"


def create_image_checksum(image: ImageFieldFile) -> str:
    if image.closed:
        image.open("rb")
    file_hash = hashlib.sha256()

    for chunk in image.chunks():
        file_hash.update(chunk)

    return file_hash.hexdigest()


def create_thumbnail(image: ImageFieldFile) -> ContentFile:
    img = PILImage.open(image)
    size = (500, 500)
    img.thumbnail(size, PILImage.LANCZOS)

    base, ext = os.path.splitext(image.name)
    thumb_name = f"{base}_thumbnail{ext}"

    thumb_io = BytesIO()
    try:
        img.save(thumb_io, img.format)
    except IOError as io_err:
        print(f"Cannot create thumbnail for [{image.id}]: {io_err}")
        raise

    return ContentFile(thumb_io.getvalue(), name=thumb_name)


def convert_to_utc(timestamp_str: str) -> datetime:
    local_time = datetime.fromisoformat(timestamp_str)
    return local_time.astimezone(pytz.utc)


def extract_datetime_stamp(exif_details: Dict[str, Any]) -> Optional[datetime.datetime]:
    date_stamp = exif_details.get("gps_datestamp")  # str, 2024:04:06
    time_stamp = exif_details.get("gps_timestamp")  # tuple

    if date_stamp and time_stamp:
        date_stamp = map(int, date_stamp.split(":"))
        time_stamp = map(int, time_stamp)
        return datetime.datetime(*date_stamp, *time_stamp, tzinfo=pytz.UTC)

    date_time_str = exif_details.get("datetime_original")
    offset_time = exif_details.get("offset_time")

    if not date_stamp or not date_time_str or offset_time is None:
        return None

    dt = datetime.datetime.strptime(date_time_str, "%Y:%m:%d %H:%M:%S")
    offset = datetime.timedelta(hours=offset_time)
    local_tz = datetime.timezone(offset)
    dt_local = dt.replace(tzinfo=local_tz)

    return dt_local.astimezone(pytz.UTC)


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


def correct_image_orientation(image_record: Image):
    image_file = PILImage.open(image_record.image)
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

    img_content = BytesIO()
    image_file.save(img_content, format=image_format)

    image_record.image = ContentFile(img_content.getvalue(), name=image_record.image.name)


def store_exif(image_record: Image) -> Dict[str, Any]:
    img = image_record.image
    if img.closed:
        img.open("rb")

    exif_image = ExifImage(img.read())

    if exif_image.has_exif is False:
        return

    exif_details = {}
    for k, v in exif_image.get_all().items():
        if isinstance(v, Enum):
            v = v.name
        elif isinstance(v, (int, float, tuple, list)):
            ...
        else:
            v = str(v).strip()

        exif_details[k] = v

    image_record.data = image_record.data or {}
    image_record.data["exif"] = exif_details
    image_record.location = extract_location(exif_details)
    image_record.photo_timestamp = extract_datetime_stamp(exif_details)


def create_classification_status(image, status, message=None):
    try:
        ClassificationStatus.objects.create(image=image, status=status, message=message)
    except Exception as err:
        print(f"Writing classification status Image {image.pk}, status: {status}: {err}")


# -------------------------------


def _modify_file_path(file_path, suffix, new_extension):
    directory, filename = os.path.split(file_path)
    name, _ = os.path.splitext(filename)
    new_filename = f"{name}{suffix}.{new_extension}"
    new_file_path = os.path.join(directory, new_filename)
    return new_file_path


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
        return DataLocation(
            storage_type="url",
            key=image.image.name,
            bucket_name=settings.IMAGE_PROCESSING_BUCKET,
        )


def _get_features_location(image: Image):
    if settings.ENVIRONMENT == "local":
        image_path = image.image.path
        features_path = _modify_file_path(image_path, "", "featurevector")
        return DataLocation("filesystem", features_path)
    else:
        image_name = image.image.name
        features_path = _modify_file_path(image_name, "", "featurevector")
        return DataLocation(
            storage_type="url",
            key=features_path,
            bucket_name=settings.IMAGE_PROCESSING_BUCKET,
        )


@transaction.atomic
def _write_classification_results(image, score_sets, label_ids, classifer_record, profile=None):
    _annotations = []
    _points = []
    label_lookup = {
        str(lbl.pk): [lbl.benthic_attribute_id, lbl.growth_form_id] for lbl in Label.objects.all()
    }
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
        for label_id, score in top_predictions[0:3]:
            ba_id, gf_id = label_lookup.get(label_id, (None, None))
            if ba_id:
                _annotations.append(
                    Annotation(
                        point=point,
                        classifier=classifer_record,
                        benthic_attribute_id=ba_id,
                        growth_form_id=gf_id,
                        score=score * 100,
                        is_confirmed=score >= 0.8,
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
        print(f"Image classification skipped, image [{image_record_id}] does not exist.")
        return

    create_classification_status(image, ClassificationStatus.RUNNING)

    try:
        data_location = _get_image_location(image)
        feature_location = _get_features_location(image)
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

        create_classification_status(image, ClassificationStatus.COMPLETED)
    except Exception as err:
        print(err)
        create_classification_status(image, ClassificationStatus.FAILED, str(err))


def classify_image_job(image_record_id, profile_id=None):
    return submit_image_job(0, _classify_image, image_record_id=image_record_id)


def classify_image(image_record_id, profile_id=None):
    _classify_image(image_record_id)
