# Generated by Django 3.2.20 on 2024-07-11 20:09

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0042_merge_0041_auto_20240612_2051_0041_auto_20240613_1200"),
    ]

    operations = [
        migrations.AlterField(
            model_name="gfcrindicatorset",
            name="indicator_set_type",
            field=models.CharField(
                choices=[("report", "Report"), ("target", "Target")], max_length=50
            ),
        ),
    ]
