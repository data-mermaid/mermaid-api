import logging

from django.conf import settings

from ..models import CollectRecord, Image, ObsBenthicPhotoQuadrat
from ..models.classification import get_image_storage_config
from . import s3 as s3_utils
from .q import submit_job

logger = logging.getLogger(__name__)

FILE_FIELDS = ("image", "thumbnail", "annotations_file", "feature_vector_file")


def _get_project_images(project_id):
    """Find all images for a project via both CollectRecord and ObsBenthicPhotoQuadrat paths."""
    cr_image_ids = set(
        Image.objects.filter(
            collect_record_id__in=CollectRecord.objects.filter(project_id=project_id).values_list(
                "id", flat=True
            )
        ).values_list("id", flat=True)
    )

    obs_image_ids = set(
        ObsBenthicPhotoQuadrat.objects.filter(
            **{f"{ObsBenthicPhotoQuadrat.project_lookup}": project_id}
        )
        .exclude(image__isnull=True)
        .values_list("image_id", flat=True)
    )

    all_image_ids = cr_image_ids | obs_image_ids
    return Image.objects.filter(id__in=all_image_ids)


def migrate_project_images(project_id, old_bucket, new_bucket, skip_delete=False):
    """Move all images for a project from old_bucket to new_bucket and update image_bucket."""
    if old_bucket == new_bucket:
        logger.info(f"Project {project_id}: buckets are the same, skipping migration")
        return 0

    images = _get_project_images(project_id)
    source_config = get_image_storage_config(old_bucket)
    dest_config = get_image_storage_config(new_bucket)

    count = 0
    for image in images.iterator():
        if image.image_bucket and image.image_bucket != old_bucket:
            continue

        try:
            _move_image_files(image, source_config, dest_config, skip_delete=skip_delete)
            image.image_bucket = new_bucket
            image.save(update_fields=["image_bucket"])
            count += 1
        except Exception:
            logger.exception(f"Failed to migrate image {image.id}")

    logger.info(f"Project {project_id}: migrated {count} images from {old_bucket} to {new_bucket}")
    return count


def _move_image_files(image, source_config, dest_config, skip_delete=False):
    """Move all file fields for a single image between buckets."""
    for field_name in FILE_FIELDS:
        field_file = getattr(image, field_name, None)
        if field_file and field_file.name:
            source_key = f"{source_config['s3_path']}{field_file.name}"
            dest_key = f"{dest_config['s3_path']}{field_file.name}"

            s3_utils.move_file_cross_account(
                source_bucket=source_config["bucket"],
                source_key=source_key,
                source_access_key=source_config["access_key"],
                source_secret_key=source_config["secret_key"],
                dest_bucket=dest_config["bucket"],
                dest_key=dest_key,
                dest_access_key=dest_config["access_key"],
                dest_secret_key=dest_config["secret_key"],
                delete_source=not skip_delete,
            )


def queue_image_migration(project_id, old_bucket, new_bucket):
    """Submit an async job to migrate project images between buckets."""
    if settings.ENVIRONMENT not in ("dev", "prod"):
        migrate_project_images(project_id, old_bucket, new_bucket)
        return

    submit_job(
        0,
        True,
        migrate_project_images,
        project_id=str(project_id),
        old_bucket=old_bucket,
        new_bucket=new_bucket,
    )
