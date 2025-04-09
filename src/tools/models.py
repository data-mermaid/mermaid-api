from django.db import models


class MERMAIDFeature(models.Model):
    label = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    enabled = models.BooleanField(default=False)

    class Meta:
        db_table = "mermaid_feature"
        verbose_name = "MERMAID Feature"

    def __str__(self):
        return self.name


class UserMERMAIDFeature(models.Model):
    feature = models.ForeignKey(MERMAIDFeature, on_delete=models.CASCADE)
    profile = models.ForeignKey("api.Profile", on_delete=models.CASCADE)
    enabled = models.BooleanField(default=False)

    class Meta:
        db_table = "user_mermaid_feature"
        verbose_name = "User MERMAID Feature"

    def __str__(self):
        return f"{self.profile}: {self.feature}"


class LogEvent(models.Model):
    timestamp = models.DateTimeField()
    event = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "log_event"

    def __str__(self):
        return f"{self.timestamp} {self.event}"


class UserMetrics(models.Model):
    date = models.DateField()
    profile = models.ForeignKey(
        "api.Profile",
        related_name="user_metrics",
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
    )
    role = models.CharField(max_length=10, null=True, blank=True)
    project_tags = models.TextField()
    countries = models.TextField()
    project_name = models.CharField(max_length=255)
    first_name = models.CharField(max_length=50, null=True, blank=True)
    last_name = models.CharField(max_length=50, null=True, blank=True)
    email = models.CharField(max_length=50, null=True, blank=True)
    project_status = models.CharField(max_length=10)
    num_submitted = models.PositiveIntegerField(default=0)
    num_summary_views = models.PositiveIntegerField(default=0)
    num_project_calls = models.PositiveIntegerField(default=0)
    num_image_uploads = models.PositiveIntegerField(default=0)
    profiles = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "user_metrics"
