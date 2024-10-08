# Generated by Django 3.2.20 on 2024-08-08 21:17

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0053_auto_20240730_2128"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="annotation",
            name="unq_conf_anno_idx",
        ),
        migrations.RemoveField(
            model_name="annotation",
            name="label",
        ),
        migrations.AddField(
            model_name="annotation",
            name="benthic_attribute",
            field=models.ForeignKey(
                default=None, on_delete=django.db.models.deletion.CASCADE, to="api.benthicattribute"
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="annotation",
            name="growth_form",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="api.growthform",
            ),
        ),
        migrations.AlterField(
            model_name="annotation",
            name="point",
            field=models.ForeignKey(
                editable=False,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="annotations",
                to="api.point",
            ),
        ),
        migrations.AddIndex(
            model_name="annotation",
            index=models.Index(
                condition=models.Q(("is_confirmed", True)),
                fields=["point", "benthic_attribute", "growth_form"],
                name="unq_conf_anno_idx",
            ),
        ),
    ]
