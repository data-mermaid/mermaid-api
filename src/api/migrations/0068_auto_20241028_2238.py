# Generated by Django 3.2.20 on 2024-10-28 22:38

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0067_merge_20241017_1341"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="gfcrindicatorset",
            name="f2_opt1",
        ),
        migrations.AddField(
            model_name="gfcrindicatorset",
            name="f2_5",
            field=models.DecimalField(
                decimal_places=3,
                default=0,
                max_digits=9,
                verbose_name="Area of non-coral reef ecosystems, e.g., mangroves, seagrass or other associated ecosystems (sq.km)",
            ),
        ),
    ]
