from time import time
from concurrent.futures import ThreadPoolExecutor

from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import Project, SummarySiteModel, SummarySiteSQLModel


class Command(BaseCommand):

    @transaction.atomic
    def update_project_summary_site(self, project_id):
        SummarySiteModel.objects.filter(project_id=project_id).delete()
        for record in SummarySiteSQLModel.objects.all().sql_table(project_id=project_id):
            values = {field.name: getattr(record, field.name) for field in SummarySiteModel._meta.fields}
            SummarySiteModel.objects.create(**values)

    def handle(self, *args, **options):
        start_time = time()
        print("Starting...")
        futures = []
        with ThreadPoolExecutor(max_workers=4) as exc:
            for project in Project.objects.filter(status__in=[Project.OPEN, Project.LOCKED]):
                futures.append(exc.submit(self.update_project_summary_site, project.pk))

        for future in futures:
            future.result()

        end_time = time()
        print(f"Done: {end_time - start_time:.3f}s")
