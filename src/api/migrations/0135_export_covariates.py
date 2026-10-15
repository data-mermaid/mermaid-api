import csv
import json
import logging
from tempfile import NamedTemporaryFile

from django.conf import settings
from django.db import migrations
from django.utils.timezone import now

from api.utils import s3

logger = logging.getLogger(__name__)

EXPORT_FIELDS = [
    "id",
    "site_id",
    "name",
    "datestamp",
    "requested_datestamp",
    "data",
    "value",
    "created_on",
    "created_by_id",
    "updated_on",
    "updated_by_id",
]
JSON_FIELDS = {"data", "value"}


def export_covariates(apps, schema_editor):
    if settings.ENVIRONMENT not in ("dev", "prod"):
        return

    Covariate = apps.get_model("api", "Covariate")
    expected_count = Covariate.objects.count()
    if expected_count == 0:
        return

    with NamedTemporaryFile(mode="w+", suffix=".csv", newline="") as tmp:
        writer = csv.writer(tmp)
        writer.writerow(EXPORT_FIELDS)
        for row in Covariate.objects.order_by("id").values(*EXPORT_FIELDS).iterator():
            writer.writerow(
                [json.dumps(row[f]) if f in JSON_FIELDS else row[f] for f in EXPORT_FIELDS]
            )
        tmp.flush()

        # Count rows from the written file rather than the loop, so a truncated
        # file is caught. Halt here so 0136 can't drop the table with an
        # incomplete backup.
        tmp.seek(0)
        exported_count = sum(1 for _ in csv.reader(tmp)) - 1
        if exported_count != expected_count:
            raise RuntimeError(
                f"Covariate export row count mismatch: exported {exported_count} "
                f"of {expected_count} rows"
            )

        timestamp = now().strftime("%Y%m%d%H%M%S")
        blob_name = f"{settings.ENVIRONMENT}/covariate_export/covariates_{timestamp}.csv"
        s3.upload_file(settings.AWS_DATA_BUCKET, tmp.name, blob_name, content_type="text/csv")

    message = f"Covariate export: wrote {exported_count} rows to {blob_name}"
    logger.info(message)
    # Migration output only reaches the deploy log via stdout (the "api"
    # logger's effective level is WARNING, so logger.info above would be
    # silently dropped).
    print(message)


class Migration(migrations.Migration):
    # No schema changes; don't hold a transaction open across the S3 upload.
    atomic = False

    dependencies = [
        ("api", "0134_classifier_config"),
    ]

    operations = [
        migrations.RunPython(
            export_covariates,
            reverse_code=migrations.RunPython.noop,
        )
    ]
