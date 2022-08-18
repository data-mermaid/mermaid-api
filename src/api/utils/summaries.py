from django.db import transaction

from ..models import Project, SummarySampleEventModel, SummarySampleEventSQLModel


def update_project_summaries(project_id, skip_test_project=True, *args, **kwargs):
    update_project_summary_sample_event(project_id, skip_test_project)


def update_project_summary_sample_event(project_id, skip_test_project=True):
    print(project_id, skip_test_project)
    if (
        skip_test_project
        and Project.objects.filter(pk=project_id, status=Project.TEST).exists()
    ):
        SummarySampleEventModel.objects.filter(project_id=project_id).delete()
        return

    with transaction.atomic():
        summary_sample_events = list(
            SummarySampleEventSQLModel.objects.all().sql_table(project_id=project_id)
        )
        SummarySampleEventModel.objects.filter(project_id=project_id).delete()
        for record in summary_sample_events:
            values = {
                field.name: getattr(record, field.name)
                for field in SummarySampleEventModel._meta.fields
            }
            SummarySampleEventModel.objects.create(**values)
