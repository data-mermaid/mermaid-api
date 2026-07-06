import csv
import uuid
from io import StringIO

from django.conf import settings
from django.contrib.gis.db import models
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.db import transaction
from pydantic import BaseModel as PydanticBaseModel, ConfigDict
from storages.backends.s3 import S3Storage

from ..utils import s3
from .base import BaseModel
from .core import CollectRecord, Project, Site
from .protocols.benthic import (
    BenthicAttribute,
    BenthicAttributeGrowthForm,
    GrowthForm,
    ObsBenthicPhotoQuadrat,
)


class ClassifierRegistrationError(Exception):
    """Raised when a model.json manifest cannot be ingested by Classifier.register()."""


SUPPORTED_MANIFEST_SCHEMA_VERSION = 1

# Maps a model.json `task` discriminator to a Classifier.classifier_type.
TASK_TO_CLASSIFIER_TYPE = {
    "pyspacer_mlp_classifier": "pyspacer",
}


class PyspacerConfig(PydanticBaseModel):
    """Validates the `config` object in a pyspacer model.json manifest."""

    model_config = ConfigDict(extra="forbid")
    patch_size: int


# Per-classifier-type pydantic schema used by Classifier.register() to validate `config`.
CONFIG_SCHEMAS = {
    "pyspacer": PyspacerConfig,
}


def select_image_storage():
    if settings.ENVIRONMENT not in ("dev", "prod"):
        return FileSystemStorage()
    return S3Storage(
        bucket_name=settings.IMAGE_PROCESSING_BUCKET,
        access_key=settings.IMAGE_BUCKET_AWS_ACCESS_KEY_ID,
        secret_key=settings.IMAGE_BUCKET_AWS_SECRET_ACCESS_KEY,
        location=settings.IMAGE_S3_PATH,
    )


def get_image_bucket(project):
    """Return the correct bucket name for a project's images."""
    if project and project.status == Project.TEST:
        return settings.IMAGE_PROCESSING_BUCKET_TEST
    return settings.IMAGE_PROCESSING_BUCKET


def get_image_bucket_for_status(status):
    """Return the correct bucket name for a given project status value."""
    if status == Project.TEST:
        return settings.IMAGE_PROCESSING_BUCKET_TEST
    return settings.IMAGE_PROCESSING_BUCKET


def get_image_storage_config(bucket=None):
    """Return bucket/creds/prefix config for a given bucket.

    In production, the test bucket uses the default AWS creds (main account),
    while the production image bucket uses the image-specific creds (separate account).
    In dev/local, IMAGE_PROCESSING_BUCKET_TEST == IMAGE_PROCESSING_BUCKET and
    IMAGE_BUCKET_AWS_* == AWS_*, so both branches return equivalent values.
    """
    is_test_bucket = (
        bucket
        and bucket == settings.IMAGE_PROCESSING_BUCKET_TEST
        and bucket != settings.IMAGE_PROCESSING_BUCKET
    )
    if is_test_bucket:
        return {
            "bucket": settings.IMAGE_PROCESSING_BUCKET_TEST,
            "access_key": settings.AWS_ACCESS_KEY_ID,
            "secret_key": settings.AWS_SECRET_ACCESS_KEY,
            "s3_path": settings.IMAGE_S3_PATH_TEST,
        }
    return {
        "bucket": settings.IMAGE_PROCESSING_BUCKET,
        "access_key": settings.IMAGE_BUCKET_AWS_ACCESS_KEY_ID,
        "secret_key": settings.IMAGE_BUCKET_AWS_SECRET_ACCESS_KEY,
        "s3_path": settings.IMAGE_S3_PATH,
    }


class LabelMapping(BaseModel):
    CORALNET = "CoralNet"
    REEFCLOUD = "ReefCloud"
    PROVIDERS = (
        (CORALNET, CORALNET),
        (REEFCLOUD, REEFCLOUD),
    )

    benthic_attribute = models.ForeignKey(
        BenthicAttribute,
        related_name="labelmappings",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    growth_form = models.ForeignKey(
        GrowthForm, related_name="labelmappings", on_delete=models.CASCADE, null=True, blank=True
    )
    provider = models.CharField(max_length=50, choices=PROVIDERS)
    provider_id = models.CharField(max_length=255)
    provider_label = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "class_label_mapping"
        constraints = [
            models.UniqueConstraint(
                fields=["benthic_attribute", "growth_form", "provider", "provider_id"],
                name="unique_labelmapping_attribute_growthform_provider",
            )
        ]

    def __str__(self):
        label = self.benthic_attribute.name if self.benthic_attribute else "(unmapped)"
        if self.growth_form:
            label += f" {self.growth_form.name}"
        return f"{label} {self.provider} {self.provider_id}"


class Classifier(BaseModel):
    CLASSIFIER_TYPES = (
        ("pyspacer", "pyspacer"),
        ("segmentation", "segmentation"),
    )

    name = models.CharField(max_length=50)
    version = models.CharField(
        max_length=11,
        unique=True,
        help_text="Classifier version (pattern: v[Version Number])",
    )
    classifier_type = models.CharField(max_length=20, choices=CLASSIFIER_TYPES, default="pyspacer")
    config = models.JSONField(default=dict, blank=True)
    description = models.TextField(max_length=1000, blank=True)
    benthic_attribute_growth_forms = models.ManyToManyField(
        BenthicAttributeGrowthForm, related_name="classifiers"
    )

    class Meta:
        db_table = "class_classifier"

    @property
    def patch_size(self):
        return self.config.get("patch_size")

    @classmethod
    def latest(cls):
        return cls.objects.order_by("-created_on").first()

    @classmethod
    def register(cls, version, *, name=None, description=None):
        """Ingest s3://<config-bucket>/classifier/<version>/model.json into this row.

        Validates config via the per-type pydantic schema and resolves each
        `ba_uuid::gf_uuid` class into the BA+GF M2M. Raises ClassifierRegistrationError
        on any malformed/mismatched manifest, applying nothing.
        """
        key = f"classifier/{version}/model.json"
        manifest = s3.read_json_object(settings.AWS_CONFIG_BUCKET, key)

        schema_version = manifest.get("schema_version")
        if schema_version != SUPPORTED_MANIFEST_SCHEMA_VERSION:
            raise ClassifierRegistrationError(
                f"Unsupported model.json schema_version {schema_version!r} for {version}"
            )

        task = manifest.get("task")
        classifier_type = TASK_TO_CLASSIFIER_TYPE.get(task)
        if classifier_type is None:
            raise ClassifierRegistrationError(f"Unknown task {task!r} in model.json for {version}")

        config_schema = CONFIG_SCHEMAS[classifier_type]
        try:
            validated_config = config_schema(**(manifest.get("config") or {}))
        except Exception as e:
            raise ClassifierRegistrationError(
                f"Invalid config in model.json for {version}: {e}"
            ) from e
        config = validated_config.model_dump()

        with transaction.atomic():
            resolved = []
            for label in manifest.get("classes", []):
                ba_uuid, _, gf_uuid = label.partition("::")
                try:
                    ba = BenthicAttribute.objects.get(pk=ba_uuid)
                except (BenthicAttribute.DoesNotExist, ValueError, ValidationError) as e:
                    raise ClassifierRegistrationError(
                        f"Unknown benthic attribute {ba_uuid!r} in class {label!r}"
                    ) from e
                gf = None
                if gf_uuid:
                    try:
                        gf = GrowthForm.objects.get(pk=gf_uuid)
                    except (GrowthForm.DoesNotExist, ValueError, ValidationError) as e:
                        raise ClassifierRegistrationError(
                            f"Unknown growth form {gf_uuid!r} in class {label!r}"
                        ) from e
                bagf, _ = BenthicAttributeGrowthForm.objects.get_or_create(
                    benthic_attribute=ba, growth_form=gf
                )
                resolved.append(bagf)

            classifier, created = cls.objects.get_or_create(
                version=version,
                defaults={
                    "name": name or version,
                    "classifier_type": classifier_type,
                    "config": config,
                    "description": description or "",
                },
            )
            if not created:
                classifier.classifier_type = classifier_type
                classifier.config = config
                if name is not None:
                    classifier.name = name
                if description is not None:
                    classifier.description = description
                classifier.save()

            classifier.benthic_attribute_growth_forms.set(resolved)

        return classifier

    def __str__(self):
        return self.version


class Image(BaseModel):
    collect_record_id = models.UUIDField(db_index=True)
    image_bucket = models.CharField(max_length=255, blank=True, default="")

    image = models.ImageField(upload_to="", storage=select_image_storage, max_length=255)
    thumbnail = models.ImageField(
        upload_to="", storage=select_image_storage, max_length=255, null=True, blank=True
    )
    annotations_file = models.FileField(
        upload_to="", storage=select_image_storage, max_length=255, null=True, blank=True
    )
    feature_vector_file = models.FileField(
        upload_to="", storage=select_image_storage, max_length=255, null=True, blank=True
    )
    name = models.CharField(max_length=200, blank=True, null=True)
    original_image_checksum = models.CharField(max_length=64, blank=True, null=True)
    original_image_name = models.CharField(max_length=200, blank=True, null=True)
    original_image_width = models.PositiveIntegerField(blank=True, null=True)
    original_image_height = models.PositiveIntegerField(blank=True, null=True)
    photo_timestamp = models.DateTimeField(null=True, blank=True)
    location = models.PointField(srid=4326, blank=True, null=True)
    comments = models.TextField(max_length=1000, blank=True, null=True)
    data = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "class_image"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.image_bucket:
            self._apply_storage()

    def __str__(self):
        return f"{self.name} - {self.original_image_name}"

    def get_storage(self):
        """Return a storage backend configured for this image's bucket."""
        if settings.ENVIRONMENT not in ("dev", "prod"):
            return FileSystemStorage()
        config = get_image_storage_config(self.image_bucket)
        return S3Storage(
            bucket_name=config["bucket"],
            access_key=config["access_key"],
            secret_key=config["secret_key"],
            location=config["s3_path"],
        )

    def _apply_storage(self):
        """Set the correct storage backend on all file fields for this instance."""
        storage = self.get_storage()
        for field_name in ("image", "thumbnail", "annotations_file", "feature_vector_file"):
            field_file = getattr(self, field_name, None)
            if field_file is not None:
                field_file.storage = storage

    def _get_first_observation(self):
        obs = ObsBenthicPhotoQuadrat.objects.filter(image=self)
        if obs.exists():
            return obs[0]

        return None

    @property
    def collect_record(self):
        return CollectRecord.objects.get_or_none(id=self.collect_record_id)

    @property
    def project(self):
        obs = self._get_first_observation()
        if obs:
            return obs.benthic_photo_quadrat_transect.quadrat_transect.sample_event.site.project
        elif self.collect_record:
            return self.collect_record.project

        return None

    @property
    def site(self):
        if self.collect_record:
            site_id = (self.collect_record.data.get("sample_event") or {}).get("site")
            if site_id:
                return Site.objects.get_or_none(id=site_id)
        else:
            obs = self._get_first_observation()
            if obs:
                return obs.benthic_photo_quadrat_transect.quadrat_transect.sample_event.site

        return None

    def create_annotations_file(self):
        csv_columns = [
            "id",
            "image_id",
            "point_id",
            "row",
            "col",
            "benthic_attribute_id",
            "benthic_attribute_name",
            "growth_form_id",
            "growth_form_name",
            "updated_on",
        ]
        annos = (
            Annotation.objects.select_related("point", "point__image")
            .filter(is_confirmed=True, point__image__id=self.id)
            .order_by("point__row", "point__column")
        )

        if not annos.exists():
            self.annotations_file.delete()
            self.annotations_file = None
            self.save()
            return

        tmp = StringIO()
        try:
            csvwriter = csv.writer(tmp)
            csvwriter.writerow(csv_columns)

            for anno in annos:
                csvwriter.writerow(
                    [
                        anno.id,
                        self.id,
                        anno.point.id,
                        anno.point.row,
                        anno.point.column,
                        anno.benthic_attribute_id,
                        anno.benthic_attribute.name,
                        anno.growth_form_id,
                        anno.growth_form.name if anno.growth_form else "",
                        anno.updated_on,
                    ]
                )
            tmp.seek(0)
            self.annotations_file.save(f"{self.id}_annotations.csv", tmp, save=True)
        finally:
            tmp.close()
            tmp = None


class Point(BaseModel):
    row = models.IntegerField()
    column = models.IntegerField()
    image = models.ForeignKey(Image, on_delete=models.CASCADE, related_name="points")

    class Meta:
        db_table = "class_point"


class Annotation(BaseModel):
    point = models.ForeignKey(
        Point, on_delete=models.CASCADE, editable=False, related_name="annotations"
    )
    benthic_attribute = models.ForeignKey(BenthicAttribute, on_delete=models.PROTECT)
    growth_form = models.ForeignKey(GrowthForm, on_delete=models.CASCADE, null=True, blank=True)
    classifier = models.ForeignKey(
        Classifier, null=True, on_delete=models.CASCADE, related_name="annotations"
    )
    score = models.PositiveSmallIntegerField(default=0, null=True, blank=True)
    is_confirmed = models.BooleanField(default=False)
    is_machine_created = models.BooleanField(default=False)

    class Meta:
        db_table = "class_annotation"
        indexes = [
            models.Index(
                fields=["point", "benthic_attribute", "growth_form"],
                name="unq_conf_anno_idx",
                condition=models.Q(is_confirmed=True),
            )
        ]

    def __str__(self):
        return f"{self.benthic_attribute} - {self.growth_form} - {self.score} - {self.is_confirmed}"


class ClassificationStatus(models.Model):
    UNKNOWN = 0
    PENDING = 1
    RUNNING = 2
    COMPLETED = 3
    FAILED = 4

    statuses = (
        (UNKNOWN, "Unknown"),
        (PENDING, "Pending"),
        (RUNNING, "Running"),
        (COMPLETED, "Completed"),
        (FAILED, "Failed"),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    image = models.ForeignKey(Image, on_delete=models.CASCADE, related_name="statuses")
    status = models.PositiveSmallIntegerField(choices=statuses, default=UNKNOWN)
    message = models.TextField(null=True, blank=True)
    data = models.JSONField(null=True, blank=True, default=dict)
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        "Profile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_created_by",
    )

    class Meta:
        db_table = "class_status"

    def __str__(self):
        return f"{self.created_on} - {self.image.name} - {self.get_status_display()}"
