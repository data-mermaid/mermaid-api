# Generated by Django 3.2.18 on 2023-04-25 21:08

from django.db import migrations


def assign_tides(apps, schema_editor):
    Tide = apps.get_model("api", "Tide")
    slack = Tide.objects.get(name="slack")
    low = Tide.objects.get(name="low")
    rising = Tide.objects.get(name="rising")
    high = Tide.objects.get(name="high")
    falling = Tide.objects.get(name="falling")

    slack.val = 10
    low.val = 20
    rising.val = 30
    high.val = 40
    falling.val = 50

    slack.save()
    low.save()
    rising.save()
    high.save()
    falling.save()


def revert_tides(apps, schema_editor):
    Tide = apps.get_model("api", "Tide")
    slack = Tide.objects.get(name="slack")
    low = Tide.objects.get(name="low")
    rising = Tide.objects.get(name="rising")
    high = Tide.objects.get(name="high")
    falling = Tide.objects.get(name="falling")

    slack.val = 10
    low.val = 10
    rising.val = 10
    high.val = 10
    falling.val = 10

    slack.save()
    low.save()
    rising.save()
    high.save()
    falling.save()


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0017_tide_val"),
    ]

    operations = [migrations.RunPython(assign_tides, revert_tides)]
