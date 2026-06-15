from django.db import migrations, models

forward_sql = """
DROP VIEW IF EXISTS vw_project_summary_sample_events;
CREATE VIEW vw_project_summary_sample_events AS
SELECT project_id, project_name, project_admins, project_notes, project_includes_gfcr,
    suggested_citation, data_policy_beltfish, data_policy_benthiclit, data_policy_benthicpit,
    data_policy_habitatcomplexity, data_policy_bleachingqc, data_policy_benthicpqt,
    data_policy_macroinvertebrate, tags, records, created_on, 'restricted'::text AS access
FROM restricted_project_summary_se
UNION ALL
SELECT project_id, project_name, project_admins, project_notes, project_includes_gfcr,
    suggested_citation, data_policy_beltfish, data_policy_benthiclit, data_policy_benthicpit,
    data_policy_habitatcomplexity, data_policy_bleachingqc, data_policy_benthicpqt,
    data_policy_macroinvertebrate, tags, records, created_on, 'unrestricted'::text AS access
FROM unrestricted_project_summary_se;
"""

reverse_sql = """
DROP VIEW IF EXISTS vw_project_summary_sample_events;
CREATE VIEW vw_project_summary_sample_events AS
SELECT project_id, project_name, project_admins, project_notes, project_includes_gfcr,
    suggested_citation, data_policy_beltfish, data_policy_benthiclit, data_policy_benthicpit,
    data_policy_habitatcomplexity, data_policy_bleachingqc, data_policy_benthicpqt,
    tags, records, created_on, 'restricted'::text AS access
FROM restricted_project_summary_se
UNION ALL
SELECT project_id, project_name, project_admins, project_notes, project_includes_gfcr,
    suggested_citation, data_policy_beltfish, data_policy_benthiclit, data_policy_benthicpit,
    data_policy_habitatcomplexity, data_policy_bleachingqc, data_policy_benthicpqt,
    tags, records, created_on, 'unrestricted'::text AS access
FROM unrestricted_project_summary_se;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0120_merge_20260610_1939"),
    ]

    operations = [
        migrations.AddField(
            model_name="projectsummarysampleeventview",
            name="data_policy_macroinvertebrate",
            field=models.CharField(default="awaiting refresh", max_length=50),
        ),
        migrations.RunSQL(forward_sql, reverse_sql),
    ]
