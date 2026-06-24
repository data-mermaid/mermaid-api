from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0126_invertattributeview"),
    ]

    operations = [
        migrations.RunSQL(
            "REFRESH MATERIALIZED VIEW mv_invert_attributes",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
