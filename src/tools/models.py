from django.db import models


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
    num_submitted = models.IntegerField(default=0)
    num_summary_views = models.IntegerField(default=0)
    num_project_calls = models.IntegerField(default=0)
    num_image_uploads = models.IntegerField(default=0)
    profiles = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "user_metrics"
