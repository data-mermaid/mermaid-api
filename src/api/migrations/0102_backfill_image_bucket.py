from django.conf import settings
from django.db import migrations


def backfill_image_bucket(apps, schema_editor):
    Image = apps.get_model("api", "Image")
    bucket = settings.IMAGE_PROCESSING_BUCKET or ""
    if bucket:
        Image.objects.filter(image_bucket="").update(image_bucket=bucket)


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0101_image_image_bucket"),
    ]

    operations = [
        migrations.RunPython(backfill_image_bucket, migrations.RunPython.noop),
    ]
