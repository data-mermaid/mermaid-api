# Generated by Django 3.2.20 on 2024-09-17 19:50

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0061_auto_20240909_1642"),
    ]

    operations = [
        migrations.AddField(
            model_name="summarysampleeventmodel",
            name="management_compliance",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="summarysampleeventmodel",
            name="management_est_year",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="summarysampleeventmodel",
            name="management_parties",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="summarysampleeventmodel",
            name="management_rules",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="summarysampleeventmodel",
            name="management_size",
            field=models.DecimalField(
                blank=True, decimal_places=3, max_digits=12, null=True, verbose_name="Size (ha)"
            ),
        ),
    ]
