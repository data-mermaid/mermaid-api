from django.db import transaction

from ..models import (
    Project,
    SummarySampleEventModel,
    SummarySampleEventSQLModel,
    SummarySiteModel,
    SummarySiteSQLModel,
)


def update_project_summaries(project_id, *args, **kwargs):
    update_project_summary_site(project_id)
    update_project_summary_sample_event(project_id)


def update_project_summary_site(project_id, skip_test_project=True):
    if (
        skip_test_project
        and Project.objects.filter(pk=project_id, status=Project.TEST).exists()
    ):
        return

    with transaction.atomic():
        summary_sites = list(SummarySiteSQLModel.objects.all().sql_table(project_id=project_id))
        SummarySiteModel.objects.filter(project_id=project_id).delete()
        for record in summary_sites:
            values = {
                field.name: getattr(record, field.name)
                for field in SummarySiteModel._meta.fields
            }
            SummarySiteModel.objects.create(**values)


def update_project_summary_sample_event(project_id, skip_test_project=True):
    if (
        skip_test_project
        and Project.objects.filter(pk=project_id, status=Project.TEST).exists()
    ):
        return

    with transaction.atomic():
        summary_sample_events = list(SummarySampleEventSQLModel.objects.all().sql_table(
            project_id=project_id
        ))
        SummarySampleEventModel.objects.filter(project_id=project_id).delete()
        for record in summary_sample_events:
            values = {
                field.name: getattr(record, field.name)
                for field in SummarySampleEventModel._meta.fields
            }
            SummarySampleEventModel.objects.create(**values)
