from datetime import timedelta

from django.db import migrations


def fix_image_collectrecord_links(apps, schema_editor):
    CollectRecord = apps.get_model("api", "CollectRecord")
    Image = apps.get_model("api", "Image")

    existing_cr_ids = set(CollectRecord.objects.values_list("id", flat=True))
    broken_images = Image.objects.exclude(collect_record_id__in=existing_cr_ids)

    for i in broken_images:
        start = i.updated_on - timedelta(days=1)
        end = i.updated_on + timedelta(days=3)

        crs = CollectRecord.objects.filter(
            updated_on__range=(start, end), data__observers__contains=[{}]
        ).extra(
            where=[
                "EXISTS (SELECT 1 FROM jsonb_array_elements(data->'observers') AS obs WHERE obs->>'profile' = %s)"
            ],
            params=[str(i.updated_by_id)],
        )

        cr_list = list(crs[:2])
        if len(cr_list) == 1:
            correct_cr = cr_list[0]
            Image.objects.filter(id=i.id).update(collect_record_id=correct_cr.id)
            print(f"Updated Image {i.id} to point to CollectRecord {correct_cr.id}")
        elif len(cr_list) == 0:
            print(f"No CollectRecord match found for Image {i.id}")
        else:
            print(f"Multiple CollectRecords matched for Image {i.id}, skipping")


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0088_auto_20250318_1506"),
    ]

    operations = [
        migrations.RunPython(fix_image_collectrecord_links, migrations.RunPython.noop),
    ]
