# Generated by Django 3.2.20 on 2025-02-13 20:28

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0085_alter_gfcrfinancesolution_sector"),
    ]

    operations = [
        migrations.AddField(
            model_name="beltfishobsmodel",
            name="project_includes_gfcr",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="beltfishsemodel",
            name="project_includes_gfcr",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="beltfishsumodel",
            name="project_includes_gfcr",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="benthiclitobsmodel",
            name="project_includes_gfcr",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="benthiclitsemodel",
            name="project_includes_gfcr",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="benthiclitsumodel",
            name="project_includes_gfcr",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="benthicphotoquadrattransectobsmodel",
            name="project_includes_gfcr",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="benthicphotoquadrattransectsemodel",
            name="project_includes_gfcr",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="benthicphotoquadrattransectsumodel",
            name="project_includes_gfcr",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="benthicpitobsmodel",
            name="project_includes_gfcr",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="benthicpitsemodel",
            name="project_includes_gfcr",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="benthicpitsumodel",
            name="project_includes_gfcr",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="bleachingqccoloniesbleachedobsmodel",
            name="project_includes_gfcr",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="bleachingqcquadratbenthicpercentobsmodel",
            name="project_includes_gfcr",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="bleachingqcsemodel",
            name="project_includes_gfcr",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="bleachingqcsumodel",
            name="project_includes_gfcr",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="habitatcomplexityobsmodel",
            name="project_includes_gfcr",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="habitatcomplexitysemodel",
            name="project_includes_gfcr",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="habitatcomplexitysumodel",
            name="project_includes_gfcr",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="summarysampleeventmodel",
            name="project_includes_gfcr",
            field=models.BooleanField(default=False),
        ),
    ]
