from time import time
from concurrent.futures import ThreadPoolExecutor

from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import Project, SummarySampleEventModel, SummarySampleEventSQLModel


class Command(BaseCommand):

    @transaction.atomic
    def update_project_summary_sample_event(self, project_id):
        SummarySampleEventModel.objects.filter(project_id=project_id).delete()
        for record in SummarySampleEventSQLModel.objects.all().sql_table(project_id=project_id):
            values = {field.name: getattr(record, field.name) for field in SummarySampleEventModel._meta.fields}
            SummarySampleEventModel.objects.create(**values)

    def handle(self, *args, **options):
        start_time = time()
        print("Updating summary sample events...")
        futures = []
        with ThreadPoolExecutor(max_workers=4) as exc:
            for project in Project.objects.filter(status__in=[Project.OPEN, Project.LOCKED]):
                futures.append(exc.submit(self.update_project_summary_sample_event, project.pk))

        for future in futures:
            future.result()

        end_time = time()
        print(f"Done: {end_time - start_time:.3f}s")
