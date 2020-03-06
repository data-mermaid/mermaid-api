from django.db import migrations


def update_region_updated_on(apps, *args, **kwargs):
    Region = apps.get_model("api", "Region")
    for r in Region.objects.all():
        r.save()


class Migration(migrations.Migration):

    dependencies = [("api", "0014_merge_20200217_1952")]

    operations = [
        migrations.RunPython(update_region_updated_on, migrations.RunPython.noop)
    ]
