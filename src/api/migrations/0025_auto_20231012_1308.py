# Generated by Django 3.2.20 on 2023-10-12 13:08

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0024_auto_20230913_1858"),
    ]

    operations = [
        migrations.AddField(
            model_name="beltfishobsmodel",
            name="project_admins",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="beltfishsemodel",
            name="project_admins",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="beltfishsumodel",
            name="project_admins",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="benthiclitobsmodel",
            name="project_admins",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="benthiclitsemodel",
            name="project_admins",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="benthiclitsumodel",
            name="project_admins",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="benthicphotoquadrattransectobsmodel",
            name="project_admins",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="benthicphotoquadrattransectsemodel",
            name="project_admins",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="benthicphotoquadrattransectsumodel",
            name="project_admins",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="benthicpitobsmodel",
            name="project_admins",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="benthicpitsemodel",
            name="project_admins",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="benthicpitsumodel",
            name="project_admins",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="bleachingqccoloniesbleachedobsmodel",
            name="project_admins",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="bleachingqcquadratbenthicpercentobsmodel",
            name="project_admins",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="bleachingqcsemodel",
            name="project_admins",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="bleachingqcsumodel",
            name="project_admins",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="habitatcomplexityobsmodel",
            name="project_admins",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="habitatcomplexitysemodel",
            name="project_admins",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="habitatcomplexitysumodel",
            name="project_admins",
            field=models.JSONField(blank=True, null=True),
        ),
    ]
