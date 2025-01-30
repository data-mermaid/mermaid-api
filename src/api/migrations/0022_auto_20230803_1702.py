# Generated by Django 3.2.18 on 2023-08-03 17:02
from django.db import migrations

from api.utils.summary_cache import add_project_to_queue


def update_cache(apps, schema_editor):
    Project = apps.get_model("api", "Project")
    for project in Project.objects.all():
        add_project_to_queue(project.pk, skip_test_project=True)


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0021_alter_beltfishobsmodel_observation_notes"),
    ]

    operations = [migrations.RunPython(update_cache, migrations.RunPython.noop)]
