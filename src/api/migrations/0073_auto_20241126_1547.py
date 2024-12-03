# Generated by Django 3.2.20 on 2024-11-26 15:47

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0072_auto_20241113_1325"),
    ]

    operations = [
        migrations.AddField(
            model_name="bleachingqccoloniesbleachedobsmodel",
            name="benthic_category",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="bleachingqccoloniesbleachedobsmodel",
            name="life_histories",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="bleachingqcsemodel",
            name="percent_cover_life_histories_avg",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="bleachingqcsemodel",
            name="percent_cover_life_histories_sd",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="bleachingqcsumodel",
            name="percent_cover_life_histories",
            field=models.JSONField(blank=True, null=True),
        ),
    ]
