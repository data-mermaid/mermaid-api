from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0100_profile_app_settings"),
    ]

    operations = [
        migrations.AddField(
            model_name="image",
            name="image_bucket",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
    ]
