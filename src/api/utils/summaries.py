from ..models import (
    SummarySampleEventModel,
    SummarySampleEventSQLModel,
    SummarySiteModel,
    SummarySiteSQLModel,
)
from ..decorators import run_in_thread


# @run_in_thread
def update_project_summaries_threaded(project_id):
    update_project_summaries(project_id=project_id)


def update_project_summaries(project_id):
    update_project_summary_site(project_id)
    update_project_summary_sample_event(project_id)


def update_project_summary_site(project_id):
    SummarySiteModel.objects.filter(project_id=project_id).delete()
    for record in SummarySiteSQLModel.objects.all().sql_table(project_id=project_id):
        values = {
            field.name: getattr(record, field.name)
            for field in SummarySiteModel._meta.fields
        }
        SummarySiteModel.objects.create(**values)


def update_project_summary_sample_event(project_id):
    SummarySampleEventModel.objects.filter(project_id=project_id).delete()
    for record in SummarySampleEventSQLModel.objects.all().sql_table(
        project_id=project_id
    ):
        values = {
            field.name: getattr(record, field.name)
            for field in SummarySampleEventModel._meta.fields
        }
        SummarySampleEventModel.objects.create(**values)
