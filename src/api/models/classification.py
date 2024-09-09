import uuid

from django.conf import settings
from django.contrib.gis.db import models
from django.core.files.storage import FileSystemStorage
from storages.backends.s3 import S3Storage

from .base import BaseModel
from .mermaid import (
    BenthicAttribute,
    BenthicAttributeGrowthForm,
    CollectRecord,
    GrowthForm,
    ObsBenthicPhotoQuadrat,
    Site,
)


def select_image_storage():
    if settings.DEBUG:
        return FileSystemStorage()
    else:
        return S3Storage(
            bucket_name=settings.IMAGE_PROCESSING_BUCKET,
            access_key=settings.IMAGE_BUCKET_AWS_ACCESS_KEY_ID,
            secret_key=settings.IMAGE_BUCKET_AWS_SECRET_ACCESS_KEY,
            location=settings.IMAGE_S3_PATH,
        )


# TODO: remove
class Label(BaseModel):
    benthic_attribute = models.ForeignKey(
        BenthicAttribute, related_name="labels", on_delete=models.CASCADE
    )
    growth_form = models.ForeignKey(
        GrowthForm, related_name="labels", on_delete=models.CASCADE, null=True, blank=True
    )
    description = models.TextField(null=True, blank=True)

    class Meta:
        unique_together = ("benthic_attribute", "growth_form")
        db_table = "class_label"
        ordering = ("benthic_attribute", "growth_form")

    def __str__(self):
        return self.name

    @property
    def name(self):
        if not self.growth_form:
            return self.benthic_attribute.name
        return f"{self.benthic_attribute.name} {self.growth_form.name}"


class LabelMapping(BaseModel):
    CORALNET = "CoralNet"
    REEFCLOUD = "ReefCloud"
    PROVIDERS = (
        (CORALNET, CORALNET),
        (REEFCLOUD, REEFCLOUD),
    )

    label = models.ForeignKey(
        Label, related_name="mappings", on_delete=models.SET_NULL, null=True, blank=True
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
        unique_together = ("benthic_attribute", "growth_form", "provider", "provider_id")
        db_table = "class_label_mapping"

    def __str__(self):
        label = self.benthic_attribute.name
        if self.growth_form:
            label += f" {self.growth_form.name}"
        return f"{label} {self.provider} {self.provider_id}"


class Classifier(BaseModel):
    name = models.CharField(max_length=50)
    version = models.CharField(
        max_length=11, help_text="Classifier version (pattern: v[Version Number])"
    )
    patch_size = models.IntegerField(help_text="Number of pixels")
    num_points = models.IntegerField(default=25)
    description = models.TextField(max_length=1000, blank=True)
    labels = models.ManyToManyField(Label, related_name="classifiers")  # TODO: remove
    benthic_attribute_growth_forms = models.ManyToManyField(
        BenthicAttributeGrowthForm, related_name="classifiers"
    )

    class Meta:
        db_table = "class_classifier"

    @classmethod
    def latest(cls):
        return cls.objects.order_by("-created_on").first()

    def __str__(self):
        return self.version


class Image(BaseModel):
    collect_record_id = models.UUIDField(db_index=True)

    image = models.ImageField(upload_to="", storage=select_image_storage, max_length=255)
    thumbnail = models.ImageField(
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

    def __str__(self):
        return f"{self.name} - {self.photo_timestamp}"

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
        cr = self.collect_record
        if cr:
            return cr.project
        else:
            obs = self._get_first_observation()
            if obs:
                return obs.benthic_photo_quadrat_transect.quadrat_transect.sample_event.site.project

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
    benthic_attribute = models.ForeignKey(BenthicAttribute, on_delete=models.CASCADE)
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
