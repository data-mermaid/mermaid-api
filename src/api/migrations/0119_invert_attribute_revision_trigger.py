from django.db import migrations
from django.utils import timezone

trigger_sql = """
    DROP TRIGGER IF EXISTS invert_attribute_trigger ON invert_attribute;
    CREATE TRIGGER invert_attribute_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "invert_attribute" FOR EACH ROW EXECUTE FUNCTION write_revision();
"""

reverse_trigger_sql = """
    DROP TRIGGER IF EXISTS invert_attribute_trigger ON invert_attribute;
"""


def backfill_invert_attribute_revisions(apps, schema_editor):
    now = timezone.now()
    InvertAttribute = apps.get_model("api", "InvertAttribute")
    InvertAttribute.objects.all().update(updated_on=now)


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0118_merge_20260602_1913"),
    ]

    operations = [
        migrations.RunSQL(sql=trigger_sql, reverse_sql=reverse_trigger_sql),
        migrations.RunPython(
            backfill_invert_attribute_revisions,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
