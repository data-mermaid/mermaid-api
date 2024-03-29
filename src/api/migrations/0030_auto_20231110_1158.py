# Generated by Django 3.2.20 on 2023-11-10 11:58

from django.db import migrations


def trigger_fishgrouping_revision(apps, schema_editor):
    FishGrouping = apps.get_model("api", "FishGrouping")
    grouping = FishGrouping.objects.first()
    grouping.save()


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0029_auto_20231109_2235"),
    ]

    operations = [migrations.RunPython(trigger_fishgrouping_revision, migrations.RunPython.noop)]
