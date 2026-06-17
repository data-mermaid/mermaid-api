from django.db import migrations

from api.models.view_models.model_view_migrations import forward_sql, reverse_sql


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0121_vw_project_summary_sample_events_macroinvertebrate"),
    ]

    operations = [
        migrations.RunSQL(forward_sql(), reverse_sql()),
    ]
