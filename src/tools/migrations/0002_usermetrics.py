# Generated by Django 3.2.20 on 2024-11-28 03:00

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0073_auto_20241128_0007"),
        ("tools", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserMetrics",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("date", models.DateField()),
                ("role", models.CharField(blank=True, max_length=10, null=True)),
                ("project_tags", models.TextField()),
                ("countries", models.TextField()),
                ("project_name", models.CharField(max_length=255)),
                ("first_name", models.CharField(blank=True, max_length=50, null=True)),
                ("last_name", models.CharField(blank=True, max_length=50, null=True)),
                ("email", models.CharField(blank=True, max_length=50, null=True)),
                ("project_status", models.CharField(max_length=10)),
                ("num_submitted", models.IntegerField(default=0)),
                ("num_summary_views", models.IntegerField(default=0)),
                ("num_project_calls", models.IntegerField(default=0)),
                ("num_image_uploads", models.IntegerField(default=0)),
                ("profiles", models.JSONField(blank=True, null=True)),
                (
                    "profile",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="user_metrics",
                        to="api.profile",
                    ),
                ),
            ],
            options={
                "db_table": "user_metrics",
            },
        ),
    ]
