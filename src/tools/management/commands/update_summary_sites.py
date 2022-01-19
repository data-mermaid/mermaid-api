from time import time
from concurrent.futures import ThreadPoolExecutor

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import Project, SummarySiteModel, SummarySiteSQLModel


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action='store_true',
            help="Ignores environment check before running update.",
        )

    @transaction.atomic
    def update_project_summary_site(self, project_id):
        SummarySiteModel.objects.filter(project_id=project_id).delete()
        for record in SummarySiteSQLModel.objects.all().sql_table(project_id=project_id):
            values = {field.name: getattr(record, field.name) for field in SummarySiteModel._meta.fields}
            SummarySiteModel.objects.create(**values)

    def handle(self, *args, **options):
        is_forced = options["force"]

        if settings.ENVIRONMENT != "prod" and is_forced is False:
            print("Skipping update")
            return

        start_time = time()
        print("Updating summary sites...")
        futures = []
        with ThreadPoolExecutor(max_workers=4) as exc:
            for project in Project.objects.filter(status__in=[Project.OPEN, Project.LOCKED]):
                futures.append(exc.submit(self.update_project_summary_site, project.pk))

        for future in futures:
            future.result()

        end_time = time()
        print(f"Done: {end_time - start_time:.3f}s")
