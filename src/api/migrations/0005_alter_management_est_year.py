# Generated by Django 3.2.15 on 2023-01-09 22:12

from django.db import migrations, models

from api.utils import validate_max_year


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0004_merge_0003_auto_20220818_1823_0003_auto_20220823_1042"),
    ]

    operations = [
        migrations.AlterField(
            model_name="management",
            name="est_year",
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                validators=[validate_max_year],
                verbose_name="year established",
            ),
        ),
    ]
