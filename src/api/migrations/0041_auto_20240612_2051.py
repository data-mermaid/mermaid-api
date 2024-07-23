# Generated by Django 3.2.20 on 2024-06-12 20:51

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0040_auto_20240523_2232"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="benthicattribute",
            name="life_history",
        ),
        migrations.AddField(
            model_name="benthicattribute",
            name="life_histories",
            field=models.ManyToManyField(blank=True, to="api.BenthicLifeHistory"),
        ),
        migrations.CreateModel(
            name="BenthicAttributeGrowthFormLifeHistory",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("created_on", models.DateTimeField(auto_now_add=True)),
                ("updated_on", models.DateTimeField(auto_now=True)),
                (
                    "attribute",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, to="api.benthicattribute"
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="benthicattributegrowthformlifehistory_created_by",
                        to="api.profile",
                    ),
                ),
                (
                    "growth_form",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, to="api.growthform"
                    ),
                ),
                (
                    "life_history",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, to="api.benthiclifehistory"
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="benthicattributegrowthformlifehistory_updated_by",
                        to="api.profile",
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "benthic attribute growth form life histories",
                "db_table": "ba_gf_life_histories",
            },
        ),
    ]