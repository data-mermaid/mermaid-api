import csv
import json
import logging
from tempfile import NamedTemporaryFile

import boto3
from django.conf import settings
from django.db import migrations, transaction
from django.utils.timezone import now

logger = logging.getLogger(__name__)


def _upload_to_s3(local_file_path, bucket, blob_name):
    client = boto3.session.Session(
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    ).client("s3")
    client.upload_file(local_file_path, bucket, blob_name, ExtraArgs={"ContentType": "text/csv"})


def export_covariates(apps, schema_editor):
    if settings.ENVIRONMENT not in ("dev", "prod"):
        return

    Covariate = apps.get_model("api", "Covariate")
    fields = ["id", "site_id", "name", "datestamp", "requested_datestamp", "data", "value"]

    # select_for_update() inside an explicit transaction takes a lock on every
    # row and gives us one consistent snapshot to count and export from, rather
    # than two separate queries (a count, then a separate iteration) that could
    # observe different rows if a concurrent write lands in between.
    with transaction.atomic():
        rows = list(Covariate.objects.select_for_update().order_by("id").values_list(*fields))

    total_count = len(rows)
    if total_count == 0:
        return

    with NamedTemporaryFile(mode="w", suffix=".csv") as tmp:
        writer = csv.writer(tmp)
        writer.writerow(fields)
        exported_count = 0
        for row in rows:
            *scalar_fields, data, value = row
            writer.writerow([*scalar_fields, json.dumps(data), json.dumps(value)])
            exported_count += 1
        tmp.flush()

        if exported_count != total_count:
            # Halt here so 0132 can't run and drop the table with an
            # incomplete backup.
            raise RuntimeError(
                f"Covariate export row count mismatch: exported {exported_count} "
                f"of {total_count} rows"
            )

        message = f"Covariate export: wrote {exported_count} rows"
        logger.info(message)
        # Migration output only reaches the deploy log via stdout (the "api"
        # logger's effective level is WARNING, so logger.info above would be
        # silently dropped).
        print(message)

        timestamp = now().strftime("%Y%m%d%H%M%S")
        blob_name = f"{settings.ENVIRONMENT}/covariate_export/covariates_{timestamp}.csv"
        _upload_to_s3(tmp.name, settings.AWS_DATA_BUCKET, blob_name)


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("api", "0130_alter_belttransectwidthcondition_options"),
    ]

    operations = [
        migrations.RunPython(
            export_covariates,
            reverse_code=migrations.RunPython.noop,
        )
    ]
