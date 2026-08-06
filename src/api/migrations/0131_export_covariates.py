import csv
import json
import logging
from tempfile import NamedTemporaryFile

from django.conf import settings
from django.db import migrations
from django.utils.timezone import now

from api.utils.s3 import upload_file

logger = logging.getLogger(__name__)


def export_covariates(apps, schema_editor):
    if settings.ENVIRONMENT not in ("dev", "prod"):
        return

    Covariate = apps.get_model("api", "Covariate")
    queryset = Covariate.objects.all()
    total_count = queryset.count()
    if total_count == 0:
        return

    fields = ["id", "site_id", "name", "datestamp", "requested_datestamp", "value"]
    with NamedTemporaryFile(mode="w", suffix=".csv") as tmp:
        writer = csv.writer(tmp)
        writer.writerow(fields)
        exported_count = 0
        for row in queryset.values_list(*fields).iterator():
            *scalar_fields, value = row
            writer.writerow([*scalar_fields, json.dumps(value)])
            exported_count += 1
        tmp.flush()

        # Migration output only reaches the deploy log via stdout (the "api" logger's
        # effective level is WARNING, so logger.info here would be silently dropped).
        if exported_count != total_count:
            message = (
                f"Covariate export row count mismatch: exported {exported_count} "
                f"of {total_count} rows"
            )
            logger.warning(message)
            print(message)
        else:
            message = f"Covariate export: wrote {exported_count} rows"
            logger.info(message)
            print(message)

        timestamp = now().strftime("%Y%m%d%H%M%S")
        blob_name = f"{settings.ENVIRONMENT}/covariate_export/covariates_{timestamp}.csv"
        upload_file(settings.AWS_DATA_BUCKET, tmp.name, blob_name, content_type="text/csv")


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
