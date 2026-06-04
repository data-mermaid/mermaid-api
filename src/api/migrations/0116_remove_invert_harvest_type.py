from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0115_goi_schema_finalize"),
    ]

    operations = [
        migrations.DeleteModel(
            name="InvertHarvestType",
        ),
    ]
