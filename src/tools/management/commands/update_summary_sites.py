from time import time
from concurrent.futures import ThreadPoolExecutor

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import EditedProject, SummarySiteModel, SummarySiteSQLModel


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action='store_true',
            help="Ignores environment check before running update.",
        )

        parser.add_argument(
            "--clear",
            action='store_true',
            help="Truncate edited projects table after updates are done.",
        )

    @transaction.atomic
    def update_project_summary_site(self, project_id):
        SummarySiteModel.objects.filter(project_id=project_id).delete()
        for record in SummarySiteSQLModel.objects.all().sql_table(project_id=project_id):
            values = {field.name: getattr(record, field.name) for field in SummarySiteModel._meta.fields}
            SummarySiteModel.objects.create(**values)

    def handle(self, *args, **options):
        is_forced = options["force"]
        clear_edited_projects = options["clear"]

        if settings.ENVIRONMENT != "prod" and is_forced is False:
            print("Skipping update")
            return

        project_ids, last_pk = EditedProject.get_projects()

        start_time = time()
        print("Updating summary sites...")
        futures = []
        with ThreadPoolExecutor(max_workers=4) as exc:
            for project_id in project_ids:
                futures.append(exc.submit(self.update_project_summary_site, project_id))

        for future in futures:
            future.result()

        if clear_edited_projects:
            EditedProject.truncate(last_pk)

        end_time = time()
        print(f"Done: {end_time - start_time:.3f}s")
