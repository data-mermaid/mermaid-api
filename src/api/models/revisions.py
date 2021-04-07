import uuid

from django.contrib.gis.db import models


class RecordRevision(models.Model):
    rev_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    table_name = models.CharField(max_length=50, db_index=True)
    record_id = models.UUIDField(db_index=True)
    project_id = models.UUIDField(null=True, blank=True, db_index=True)
    profile_id = models.UUIDField(null=True, blank=True)
    updated_on = models.DateTimeField(auto_now=True)
    deleted = models.BooleanField(default=False)

    class Meta:
        db_table = "record_revision"

    def __str__(self):
        return f"[{self.rev_id} {self.updated_on}] {self.table_name} {self.record_id}"


class TableRevision(models.Model):
    last_rev_id = models.UUIDField(db_index=True)
    table_name = models.CharField(max_length=50, db_index=True)
    updated_on = models.DateTimeField()
    project_id = models.UUIDField(null=True, blank=True, db_index=True)

    class Meta:
        db_table = "table_revision"
        unique_together = ("table_name", "project_id")

    def __str__(self):
        return f"[{self.last_rev_id}] {self.table_name} - {self.updated_on}"
