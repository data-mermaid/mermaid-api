import copy
import logging
import re
import uuid
from collections import defaultdict

import botocore.exceptions
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.db.models.fields.related import OneToOneField
from django.utils import timezone
from django.utils.text import slugify

from ..models import (
    BLEACHINGQC_PROTOCOL,
    PROTOCOL_MAP,
    BeltFish,
    BenthicLIT,
    BenthicPhotoQuadratTransect,
    BenthicPIT,
    BenthicTransect,
    BleachingQuadratCollection,
    CollectRecord,
    FishBeltTransect,
    HabitatComplexity,
    Management,
    ObsBeltFish,
    ObsBenthicLIT,
    ObsBenthicPhotoQuadrat,
    ObsBenthicPIT,
    ObsColoniesBleached,
    Observer,
    ObsHabitatComplexity,
    ObsQuadratBenthicPercent,
    Project,
    ProjectProfile,
    QuadratCollection,
    QuadratTransect,
    SampleEvent,
    SampleUnit,
    Site,
    TransectMethod,
)
from ..models.classification import (
    Annotation,
    ClassificationStatus,
    Image,
    Point,
    get_image_bucket,
    get_image_storage_config,
)
from . import delete_instance_and_related_objects, get_value, is_uuid, s3 as s3_utils
from .email import mermaid_email

logger = logging.getLogger(__name__)

UUID_PATTERN = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE
)


class ImageCopyError(Exception):
    """Raised when source image files cannot be found in S3 during project copy."""

    pass


def _generate_new_image_path(old_path, new_image_id):
    # Replace the UUID in the filename portion with the new image ID
    parts = old_path.rsplit("/", 1)
    if len(parts) == 2:
        directory, filename = parts
        new_filename = UUID_PATTERN.sub(str(new_image_id), filename, count=1)
        return f"{directory}/{new_filename}"
    else:
        return UUID_PATTERN.sub(str(new_image_id), old_path, count=1)


class S3CopyTracker:
    """
    Prevents orphaned S3 files when a database transaction fails after
    S3 files have been copied. It tracks all copied files and provides a cleanup
    method to delete them if needed.
    """

    def __init__(self):
        self.copied_files = []

    def copy_file(
        self, source_path, new_image_id, source_bucket=None, source_config=None, dest_config=None
    ):
        if not source_path:
            return None

        new_path = _generate_new_image_path(source_path, new_image_id)

        if dest_config is None:
            dest_config = get_image_storage_config()
        if source_config is None:
            source_config = dest_config
        if source_bucket is None:
            source_bucket = source_config["bucket"]

        source_key = f"{source_config['s3_path']}{source_path}"
        dest_key = f"{dest_config['s3_path']}{new_path}"

        # Use cross-account move (without delete) when credentials differ
        try:
            s3_utils.move_file_cross_account(
                source_bucket=source_bucket,
                source_key=source_key,
                source_access_key=source_config["access_key"],
                source_secret_key=source_config["secret_key"],
                dest_bucket=dest_config["bucket"],
                dest_key=dest_key,
                dest_access_key=dest_config["access_key"],
                dest_secret_key=dest_config["secret_key"],
                delete_source=False,
            )
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise ImageCopyError(
                    f"Source image file not found: {source_key} in bucket {source_bucket}"
                ) from e
            raise
        self.copied_files.append((dest_config, new_path))
        return new_path

    def cleanup(self):
        for dest_config, path in self.copied_files:
            try:
                full_key = f"{dest_config['s3_path']}{path}"
                s3_utils.delete_file(
                    bucket=dest_config["bucket"],
                    blob_name=full_key,
                    aws_access_key_id=dest_config["access_key"],
                    aws_secret_access_key=dest_config["secret_key"],
                )
                logger.info(f"Cleaned up S3 file: {path}")
            except Exception as e:
                logger.error(f"Failed to cleanup S3 file {path}: {e}")


def _copy_image(source_image, s3_tracker, dest_bucket=None, collect_record_id=None):
    """Copy an Image record and its S3 files, including Annotations.

    Args:
        source_image: The Image instance to copy
        s3_tracker: S3CopyTracker instance for tracking copied files
        dest_bucket: Target bucket name for the new image
        collect_record_id: UUID to use as the collect_record_id on the copied image.
            If None, falls back to the new image's own ID.

    Raises:
        Exception: If S3 copy fails (propagates to trigger cleanup)
    """
    source_image_id = source_image.id
    new_image_id = uuid.uuid4()

    source_bucket = source_image.image_bucket or settings.IMAGE_PROCESSING_BUCKET
    source_config = get_image_storage_config(source_bucket)
    dest_config = (
        get_image_storage_config(dest_bucket) if dest_bucket else get_image_storage_config()
    )

    # Copy S3 files - raises on failure (triggers rollback + cleanup)
    # Skip annotations_file - will be regenerated
    new_image_path = s3_tracker.copy_file(
        source_image.image.name if source_image.image else None,
        new_image_id,
        source_bucket=source_bucket,
        source_config=source_config,
        dest_config=dest_config,
    )
    new_thumbnail_path = s3_tracker.copy_file(
        source_image.thumbnail.name if source_image.thumbnail else None,
        new_image_id,
        source_bucket=source_bucket,
        source_config=source_config,
        dest_config=dest_config,
    )
    new_feature_vector_path = s3_tracker.copy_file(
        source_image.feature_vector_file.name if source_image.feature_vector_file else None,
        new_image_id,
        source_bucket=source_bucket,
        source_config=source_config,
        dest_config=dest_config,
    )

    # Use the provided collect_record_id so that all images for a copied BPQ share the
    # same value, allowing the serializer to look them up.  Falls back to the new image's
    # own ID for non-BPQ copies where the linkage isn't needed.
    new_image = Image(
        id=new_image_id,
        collect_record_id=collect_record_id or new_image_id,
        image_bucket=dest_bucket or settings.IMAGE_PROCESSING_BUCKET,
        name=source_image.name,
        original_image_checksum=source_image.original_image_checksum,
        original_image_name=source_image.original_image_name,
        original_image_width=source_image.original_image_width,
        original_image_height=source_image.original_image_height,
        photo_timestamp=source_image.photo_timestamp,
        location=source_image.location,
        comments=source_image.comments,
        data=copy.deepcopy(source_image.data) if source_image.data else None,
        created_by=source_image.created_by,
        updated_by=source_image.updated_by,
    )

    if new_image_path:
        new_image.image.name = new_image_path
    if new_thumbnail_path:
        new_image.thumbnail.name = new_thumbnail_path
    if new_feature_vector_path:
        new_image.feature_vector_file.name = new_feature_vector_path

    # Set created_on so pre_image_save signal skips validation/normalization
    # (copied images are already processed; auto_now_add will override this for the DB insert)
    new_image.created_on = source_image.created_on
    new_image.save()

    for point in Point.objects.filter(image_id=source_image_id):
        old_point_id = point.id
        point.id = None
        point.image_id = new_image.id
        point.save()

        annotations_to_create = []
        for annotation in Annotation.objects.filter(point_id=old_point_id):
            annotation.id = None
            annotation.point_id = point.id
            annotations_to_create.append(annotation)
        if annotations_to_create:
            Annotation.objects.bulk_create(annotations_to_create)

    new_image.create_annotations_file()

    # Copy the latest ClassificationStatus so the webapp knows the image has been processed
    latest_status = source_image.statuses.order_by("-created_on").first()
    if latest_status:
        ClassificationStatus.objects.create(
            image=new_image,
            status=latest_status.status,
            message=latest_status.message,
            data=copy.deepcopy(latest_status.data) if latest_status.data else None,
            created_by=latest_status.created_by,
        )

    return new_image


def _get_sample_unit_method_label(sample_unit_method, sample_unit_name):
    number_label = []
    sample_unit = getattr(sample_unit_method, sample_unit_name)
    if hasattr(sample_unit, "number") and sample_unit.number is not None:
        number_label.append(str(sample_unit.number))
    elif sample_unit_method.protocol == BLEACHINGQC_PROTOCOL:
        number_label.append("1")

    if hasattr(sample_unit, "label") and sample_unit.label.strip():
        number_label.append(sample_unit.label)

    return " ".join(number_label)


def get_sample_unit_field(model):
    return next(
        (
            field.name
            for field in model._meta.get_fields()
            if isinstance(field, OneToOneField) and issubclass(field.related_model, SampleUnit)
        ),
        None,
    )


def _create_submitted_sample_unit_method_summary(model_cls, project):
    DEFAULT_UPDATED_BY = "N/A"
    summary = defaultdict(dict)
    protocol = model_cls.protocol
    sample_unit_name = get_sample_unit_field(model_cls)

    if sample_unit_name is None:
        return summary

    qry_filter = {f"{sample_unit_name}__sample_event__site__project_id": project}
    queryset = model_cls.objects.select_related(
        f"{sample_unit_name}",
        f"{sample_unit_name}__sample_event",
        f"{sample_unit_name}__sample_event__site",
        f"{sample_unit_name}__sample_event__management",
        "updated_by",
    ).prefetch_related("observers")
    queryset = queryset.filter(**qry_filter)

    for record in queryset:
        sample_unit = getattr(record, sample_unit_name)
        sample_event = sample_unit.sample_event
        site = sample_event.site
        management = sample_event.management
        site_id = str(site.pk)
        label = _get_sample_unit_method_label(record, sample_unit_name)
        updated_by = DEFAULT_UPDATED_BY
        if sample_unit.updated_by:
            updated_by = sample_unit.updated_by.full_name
        observers = [o.profile_name for o in record.observers.all()]

        if site_id not in summary:
            summary[site_id] = {"site_name": "", "sample_unit_methods": {protocol: []}}

        summary[site_id]["site_name"] = site.name
        summary[site_id]["sample_unit_methods"][protocol].append(
            {
                "id": f"{record.pk}",
                "sample_date": sample_event.sample_date,
                "label": label,
                "management": {
                    "id": management.id,
                    "name": management.name,
                },
                "updated_by": updated_by,
                "observers": observers,
            }
        )

    for site_id in summary:
        s = sorted(
            summary[site_id]["sample_unit_methods"][protocol],
            key=lambda e: f'{e["label"]}:-:{e["sample_date"]}',
        )
        summary[site_id]["sample_unit_methods"][protocol] = s

    return summary


def create_submitted_summary(project):
    summary = {}
    protocols = []
    sample_unit_methods = TransectMethod.__subclasses__()
    for sample_unit_method in sample_unit_methods:
        sample_unit_method_summary = _create_submitted_sample_unit_method_summary(
            sample_unit_method, project
        )

        if not sample_unit_method_summary:
            continue

        protocols.append(sample_unit_method.protocol)
        for site_id in sample_unit_method_summary:
            if site_id not in summary:
                summary[site_id] = sample_unit_method_summary[site_id]
            else:
                summary[site_id]["sample_unit_methods"].update(
                    sample_unit_method_summary[site_id]["sample_unit_methods"]
                )

    return protocols, summary


def _get_collect_record_label(collect_record):
    number_label = []
    sample_unit = collect_record.sample_unit
    number = sample_unit.get("number")
    if collect_record.protocol == BLEACHINGQC_PROTOCOL and number is None:
        number = 1
    label = sample_unit.get("label") or ""
    if number is not None:
        number_label.append(str(number))

    if label.strip():
        number_label.append(label)

    return " ".join(number_label)


def create_collecting_summary(project):
    DEFAULT_SITE_ID = "__null__"
    DEFAULT_MR_ID = "__null__"
    DEFAULT_OBSERVER_NAME = "unnamed observer"
    summary = {}
    collect_records = CollectRecord.objects.select_related("profile").filter(project=project)

    site_ids = []
    mr_ids = []
    for collect_record in collect_records:
        site_id = get_value(collect_record.data or {}, "sample_event.site", ".")
        if is_uuid(site_id) is False:
            continue
        site_ids.append(site_id)
        mr_id = get_value(collect_record.data or {}, "sample_event.management", ".")
        if is_uuid(mr_id) is False:
            continue
        mr_ids.append(mr_id)

    sites = Site.objects.filter(id__in=set(site_ids))
    site_lookup = {str(s.pk): s.name for s in sites}
    managements = Management.objects.filter(id__in=set(mr_ids))
    mr_lookup = {str(mr.pk): mr.name for mr in managements}

    protocols = {}

    for collect_record in collect_records:
        data = collect_record.data or {}
        protocol = get_value(data, "protocol")

        if protocol not in PROTOCOL_MAP:
            continue

        protocols[protocol] = None

        profile = collect_record.profile
        site_id = get_value(data, "sample_event.site", ".")
        if site_id not in site_lookup:
            site_id = DEFAULT_SITE_ID
        mr_id = get_value(data, "sample_event.management", ".")
        if mr_id not in mr_lookup:
            mr_id = DEFAULT_MR_ID

        profile_id = str(profile.pk)

        if site_id not in summary:
            summary[site_id] = {
                "site_name": site_lookup.get(site_id) or DEFAULT_SITE_ID,
                "sample_unit_methods": {protocol: {"profile_summary": {}}},
            }

        if protocol not in summary[site_id]["sample_unit_methods"]:
            summary[site_id]["sample_unit_methods"][protocol] = {"profile_summary": {}}

        if profile_id not in summary[site_id]["sample_unit_methods"][protocol]["profile_summary"]:
            summary[site_id]["sample_unit_methods"][protocol]["profile_summary"][profile_id] = {
                "profile_name": profile.full_name,
                "collect_records": [],
            }

        label = _get_collect_record_label(collect_record)
        sample_date = get_value(data, "sample_event__sample_date")
        mr = mr_lookup.get(mr_id) or DEFAULT_MR_ID
        observers = get_value(data, "observers") or []
        observer_names = [o.get("profile_name") or DEFAULT_OBSERVER_NAME for o in observers]

        summary[site_id]["sample_unit_methods"][protocol]["profile_summary"][profile_id][
            "collect_records"
        ].append(
            {
                "name": label,
                "sample_date": sample_date,
                "management_name": mr,
                "observers": observer_names,
            }
        )

    return list(protocols), summary


def _copy_related_objects(queryset, new_project, track_ids=False):
    """
    If track_ids=True, returns a dict mapping old IDs to new IDs.
    If track_ids=False, uses bulk_create for performance.
    """
    if track_ids:
        id_map = {}
        for obj in queryset:
            old_id = str(obj.id)
            new_obj = copy.copy(obj)
            new_obj.id = None
            new_obj.project = new_project
            new_obj.save()
            id_map[old_id] = str(new_obj.id)
        return id_map
    else:
        objects = []
        for obj in queryset:
            new_obj = copy.copy(obj)
            new_obj.id = None
            new_obj.project = new_project
            objects.append(new_obj)
        if objects:
            type(objects[0]).objects.bulk_create(objects)
        return {}


@transaction.atomic()
def copy_project_and_resources(owner_profile, new_project_name, original_project):
    is_demo = str(original_project.pk) == str(settings.DEMO_PROJECT_ID)

    new_project = Project.objects.get(id=original_project.pk)
    new_project.id = None
    new_project.name = new_project_name
    new_project.created_by = owner_profile
    new_project.updated_by = owner_profile
    if is_demo:
        new_project.is_demo = True
    new_project.save()

    new_project.tags.add(*original_project.tags.all())

    ProjectProfile.objects.create(
        role=ProjectProfile.ADMIN, project=new_project, profile=owner_profile
    )

    project_profiles = []
    for pp in original_project.profiles.filter(~Q(profile=owner_profile)):
        pp.id = None
        pp.project = new_project
        project_profiles.append(pp)
    ProjectProfile.objects.bulk_create(project_profiles)

    site_id_map = _copy_related_objects(
        original_project.sites.all(), new_project, track_ids=is_demo
    )
    management_id_map = _copy_related_objects(
        original_project.management_set.all(), new_project, track_ids=is_demo
    )

    if is_demo:
        original_project_fresh = Project.objects.get(id=settings.DEMO_PROJECT_ID)
        dest_bucket = get_image_bucket(new_project)
        s3_tracker = S3CopyTracker()
        try:
            copy_project_data(
                original_project=original_project_fresh,
                new_project=new_project,
                site_id_map=site_id_map,
                management_id_map=management_id_map,
                s3_tracker=s3_tracker,
                dest_bucket=dest_bucket,
            )
        except Exception:
            # S3 files were copied but DB will rollback - clean up S3 files
            logger.error("Project copy failed, cleaning up S3 files")
            s3_tracker.cleanup()
            raise

    return new_project


def copy_project_data(
    original_project, new_project, site_id_map, management_id_map, s3_tracker, dest_bucket=None
):
    _copy_collect_records(original_project, new_project, site_id_map, management_id_map)
    _copy_submitted_data(site_id_map, management_id_map, s3_tracker, dest_bucket=dest_bucket)


def _copy_collect_records(original_project, new_project, site_id_map, management_id_map):
    for cr in original_project.collect_records.all():
        new_data = copy.deepcopy(cr.data) if cr.data else {}

        if new_data.get("sample_event"):
            old_site = new_data["sample_event"].get("site")
            if old_site and str(old_site) in site_id_map:
                new_data["sample_event"]["site"] = site_id_map[str(old_site)]

            old_mgmt = new_data["sample_event"].get("management")
            if old_mgmt and str(old_mgmt) in management_id_map:
                new_data["sample_event"]["management"] = management_id_map[str(old_mgmt)]

        # Preserve original observers - don't replace them

        CollectRecord.objects.create(
            project=new_project,
            profile=cr.profile,
            data=new_data,
            validations=copy.deepcopy(cr.validations) if cr.validations else None,
            stage=cr.stage,
            created_by=cr.created_by,
            updated_by=cr.updated_by,
        )


def _copy_submitted_data(site_id_map, management_id_map, s3_tracker, dest_bucket=None):
    old_site_ids = [uuid.UUID(k) for k in site_id_map.keys()]
    sample_event_id_map = {}

    for se in SampleEvent.objects.filter(site_id__in=old_site_ids):
        old_se_id = str(se.id)
        old_se_created_by = se.created_by
        old_se_updated_by = se.updated_by

        new_site_id = site_id_map.get(str(se.site_id))
        if new_site_id is None:
            logger.error(f"SampleEvent {old_se_id}: site_id {se.site_id} not found in site_id_map")
            raise ValueError(f"SampleEvent {old_se_id} references unmapped site {se.site_id}")

        new_management_id = management_id_map.get(str(se.management_id))
        if new_management_id is None:
            logger.error(
                f"SampleEvent {old_se_id}: management_id {se.management_id} "
                f"not found in management_id_map"
            )
            raise ValueError(
                f"SampleEvent {old_se_id} references unmapped management {se.management_id}"
            )

        se.id = None
        se.site_id = uuid.UUID(new_site_id)
        se.management_id = uuid.UUID(new_management_id)
        se.created_by = old_se_created_by
        se.updated_by = old_se_updated_by
        se.save()
        sample_event_id_map[old_se_id] = str(se.id)

    _copy_benthic_transects(sample_event_id_map)
    _copy_fish_belt_transects(sample_event_id_map)
    _copy_quadrat_collections(sample_event_id_map)
    _copy_quadrat_transects(sample_event_id_map, s3_tracker, dest_bucket=dest_bucket)


def _copy_benthic_transects(sample_event_id_map):
    """Copy BenthicTransect hierarchy (BenthicLIT, BenthicPIT, HabitatComplexity)."""
    old_se_ids = [uuid.UUID(k) for k in sample_event_id_map.keys()]

    for bt in BenthicTransect.objects.filter(sample_event_id__in=old_se_ids):
        old_bt_id = bt.id
        old_bt_created_by = bt.created_by
        old_bt_updated_by = bt.updated_by
        bt.id = None
        bt.sample_event_id = uuid.UUID(sample_event_id_map[str(bt.sample_event_id)])
        bt.collect_record_id = None
        bt.created_by = old_bt_created_by
        bt.updated_by = old_bt_updated_by
        bt.save()

        for lit in BenthicLIT.objects.filter(transect_id=old_bt_id):
            _copy_transect_method(lit, bt.id, ObsBenthicLIT, "benthiclit")

        for pit in BenthicPIT.objects.filter(transect_id=old_bt_id):
            _copy_transect_method(pit, bt.id, ObsBenthicPIT, "benthicpit")

        for hc in HabitatComplexity.objects.filter(transect_id=old_bt_id):
            _copy_transect_method(hc, bt.id, ObsHabitatComplexity, "habitatcomplexity")


def _copy_fish_belt_transects(sample_event_id_map):
    """Copy FishBeltTransect hierarchy (BeltFish)."""
    old_se_ids = [uuid.UUID(k) for k in sample_event_id_map.keys()]

    for fbt in FishBeltTransect.objects.filter(sample_event_id__in=old_se_ids):
        old_fbt_id = fbt.id
        old_fbt_created_by = fbt.created_by
        old_fbt_updated_by = fbt.updated_by
        fbt.id = None
        fbt.sample_event_id = uuid.UUID(sample_event_id_map[str(fbt.sample_event_id)])
        fbt.collect_record_id = None
        fbt.created_by = old_fbt_created_by
        fbt.updated_by = old_fbt_updated_by
        fbt.save()

        for bf in BeltFish.objects.filter(transect_id=old_fbt_id):
            _copy_transect_method(bf, fbt.id, ObsBeltFish, "beltfish")


def _copy_quadrat_collections(sample_event_id_map):
    """Copy QuadratCollection hierarchy (BleachingQuadratCollection)."""
    old_se_ids = [uuid.UUID(k) for k in sample_event_id_map.keys()]

    for qc in QuadratCollection.objects.filter(sample_event_id__in=old_se_ids):
        old_qc_id = qc.id
        old_qc_created_by = qc.created_by
        old_qc_updated_by = qc.updated_by
        qc.id = None
        qc.sample_event_id = uuid.UUID(sample_event_id_map[str(qc.sample_event_id)])
        qc.collect_record_id = None
        qc.created_by = old_qc_created_by
        qc.updated_by = old_qc_updated_by
        qc.save()

        for bqc in BleachingQuadratCollection.objects.filter(quadrat_id=old_qc_id):
            old_bqc_id = bqc.id
            old_bqc_created_by = bqc.created_by
            old_bqc_updated_by = bqc.updated_by
            bqc.pk = None
            bqc.id = None
            # Clear the parent pointer for multi-table inheritance
            bqc.transectmethod_ptr_id = None
            bqc.quadrat_id = qc.id
            bqc.collect_record_id = None
            bqc.created_by = old_bqc_created_by
            bqc.updated_by = old_bqc_updated_by
            bqc.save()

            _copy_observations(
                ObsColoniesBleached,
                "bleachingquadratcollection_id",
                old_bqc_id,
                bqc.id,
            )
            _copy_observations(
                ObsQuadratBenthicPercent,
                "bleachingquadratcollection_id",
                old_bqc_id,
                bqc.id,
            )
            _copy_observers(old_bqc_id, bqc.id)


def _copy_quadrat_transects(sample_event_id_map, s3_tracker, dest_bucket=None):
    """Copy QuadratTransect hierarchy (BenthicPhotoQuadratTransect) with images."""
    old_se_ids = [uuid.UUID(k) for k in sample_event_id_map.keys()]

    for qt in QuadratTransect.objects.filter(sample_event_id__in=old_se_ids):
        old_qt_id = qt.id
        old_qt_created_by = qt.created_by
        old_qt_updated_by = qt.updated_by
        qt.id = None
        qt.sample_event_id = uuid.UUID(sample_event_id_map[str(qt.sample_event_id)])
        qt.collect_record_id = None
        qt.created_by = old_qt_created_by
        qt.updated_by = old_qt_updated_by
        qt.save()

        for bpqt in BenthicPhotoQuadratTransect.objects.filter(quadrat_transect_id=old_qt_id):
            old_bpqt_id = bpqt.id
            old_bpqt_created_by = bpqt.created_by
            old_bpqt_updated_by = bpqt.updated_by
            # Generate a synthetic collect_record_id so that the serializer can
            # look up copied images via Image.collect_record_id == bpqt.collect_record_id.
            synthetic_cr_id = uuid.uuid4()
            bpqt.pk = None
            bpqt.id = None
            # Clear the parent pointer for multi-table inheritance
            bpqt.transectmethod_ptr_id = None
            bpqt.quadrat_transect_id = qt.id
            bpqt.collect_record_id = synthetic_cr_id
            bpqt.created_by = old_bpqt_created_by
            bpqt.updated_by = old_bpqt_updated_by
            bpqt.save()

            # Build image ID map to avoid copying the same image multiple times
            # (multiple observations can reference the same image)
            image_id_map = {}

            for obs in ObsBenthicPhotoQuadrat.objects.filter(
                benthic_photo_quadrat_transect_id=old_bpqt_id
            ):
                old_image_id = obs.image_id
                old_obs_created_by = obs.created_by
                old_obs_updated_by = obs.updated_by
                new_image_id = None

                if old_image_id:
                    if old_image_id not in image_id_map:
                        new_image = _copy_image(
                            obs.image,
                            s3_tracker,
                            dest_bucket=dest_bucket,
                            collect_record_id=synthetic_cr_id,
                        )
                        image_id_map[old_image_id] = new_image.id
                    new_image_id = image_id_map[old_image_id]

                obs.id = None
                obs.benthic_photo_quadrat_transect_id = bpqt.id
                obs.image_id = new_image_id
                obs.created_by = old_obs_created_by
                obs.updated_by = old_obs_updated_by
                obs.save()

            _copy_observers(old_bpqt_id, bpqt.id)


def _copy_transect_method(tm, new_transect_id, obs_model, obs_fk_name):
    old_tm_id = tm.id
    old_created_by = tm.created_by
    old_updated_by = tm.updated_by
    tm.pk = None
    tm.id = None
    # Clear the parent pointer for multi-table inheritance
    tm.transectmethod_ptr_id = None
    tm.transect_id = new_transect_id
    tm.collect_record_id = None
    tm.created_by = old_created_by
    tm.updated_by = old_updated_by
    tm.save()

    _copy_observations(obs_model, f"{obs_fk_name}_id", old_tm_id, tm.id)
    _copy_observers(old_tm_id, tm.id)


def _copy_observations(obs_model, fk_field, old_parent_id, new_parent_id):
    new_observations = []
    for obs in obs_model.objects.filter(**{fk_field: old_parent_id}):
        new_obs = copy.copy(obs)
        new_obs.id = None
        setattr(new_obs, fk_field, new_parent_id)
        # created_by and updated_by preserved via copy.copy
        new_observations.append(new_obs)
    if new_observations:
        obs_model.objects.bulk_create(new_observations)


def _copy_observers(old_tm_id, new_tm_id):
    """Copy ALL original observers instead of creating a single new one."""
    new_observers = []
    for obs in Observer.objects.filter(transectmethod_id=old_tm_id):
        new_obs = copy.copy(obs)
        new_obs.id = None
        new_obs.transectmethod_id = new_tm_id
        # created_by and updated_by preserved via copy.copy
        new_observers.append(new_obs)
    if new_observers:
        Observer.objects.bulk_create(new_observers)


def email_members_of_new_project(project, owner_profile):
    for project_profile in project.profiles.filter(~Q(profile=owner_profile)):
        context = {
            "owner": owner_profile,
            "project": project,
            "project_profile": project_profile,
        }
        mermaid_email(
            subject="New Project",
            template="emails/added_to_project.txt",
            to=[project_profile.profile.email],
            context=context,
        )


def get_safe_project_name(project_id):
    try:
        project = Project.objects.get(id=project_id)
        return slugify(project.name, allow_unicode=True).replace("-", "_")
    except Project.DoesNotExist as e:
        raise ValueError(f"Project with id '{project_id}' does not exist") from e


def get_profiles(project):
    return project.profiles.order_by("profile__last_name", "profile__first_name")


def citation_retrieved_text(project_name):
    date_text = timezone.localdate().strftime("%B %-d, %Y")
    domain = settings.DEFAULT_DOMAIN_DASHBOARD
    return f"Retrieved {date_text} from {domain}?project={project_name}."


def default_citation(project, profiles=None):
    if profiles is None:
        profiles = get_profiles(project)
    admin_names = [
        p.profile.citation_name
        for p in profiles
        if p.is_admin is True and p.profile.citation_name is not None
    ]
    year = ""
    latest_se = SampleEvent.objects.filter(site__project=project).order_by("-sample_date").first()
    if latest_se and latest_se.sample_date:
        year = f"{latest_se.sample_date.year}. "
    return f"{', '.join(admin_names)}. {year}{project.name}. MERMAID."


def suggested_citation(project, profiles=None):
    if project is None:
        raise ValueError("Project cannot be None")
    if project.user_citation and project.user_citation.strip():
        return project.user_citation.strip()
    return default_citation(project, profiles)


def delete_project(pk):
    try:
        instance = Project.objects.get(id=pk)
    except Project.DoesNotExist:
        print(f"project {pk} does not exist")
        return

    with transaction.atomic():
        sid = transaction.savepoint()
        try:
            delete_instance_and_related_objects(instance)
            transaction.savepoint_commit(sid)
            print("project deleted")
        except Exception as err:
            print(f"Delete Project: {err}")
            transaction.savepoint_rollback(sid)
