from django.db import models


class LogEvent(models.Model):
    timestamp = models.DateTimeField()
    event = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "log_event"

    def __str__(self):
        return f"{self.timestamp} {self.event}"
