# Generated by Django 3.2.20 on 2024-10-07 22:26

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0063_auto_20240919_1546"),
    ]

    operations = [
        migrations.AddField(
            model_name="benthicphotoquadrattransect",
            name="image_classification",
            field=models.BooleanField(default=False),
        ),
    ]
