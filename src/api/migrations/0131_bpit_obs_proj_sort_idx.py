from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations, models


class Migration(migrations.Migration):
    # CREATE INDEX CONCURRENTLY can't run in a transaction.
    atomic = False

    dependencies = [
        ("api", "0130_alter_belttransectwidthcondition_options"),
    ]

    operations = [
        AddIndexConcurrently(
            model_name="benthicpitobsmodel",
            index=models.Index(
                fields=[
                    "project_id",
                    "site_name",
                    "sample_date",
                    "transect_number",
                    "label",
                    "interval",
                    "id",
                ],
                name="bpit_obs_proj_sort_idx",
            ),
        ),
    ]
