from time import time
from concurrent.futures import ThreadPoolExecutor

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import Project
from api.utils.summaries import update_project_summaries


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action='store_true',
            help="Ignores environment check before running update.",
        )
        parser.add_argument(
            "--test_projects",
            action='store_true',
            help="Include test_projects when running update.",
        )

    @transaction.atomic
    def update_summaries(self, project_id, skip_test_project):
        update_project_summaries(project_id, skip_test_project)

    def handle(self, *args, **options):
        is_forced = options["force"]
        skip_test_project = options["test_projects"] is not True

        if settings.ENVIRONMENT not in ("dev", "prod") and is_forced is False:
            print("Skipping update")
            return

        start_time = time()
        print("Updating summaries...")
        futures = []
        with ThreadPoolExecutor(max_workers=4) as exc:
            for project in Project.objects.all():
                futures.append(exc.submit(self.update_summaries, project.pk, skip_test_project))

        for future in futures:
            future.result()

        end_time = time()
        print(f"Done: {end_time - start_time:.3f}s")
