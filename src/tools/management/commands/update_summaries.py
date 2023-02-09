from time import time
from concurrent.futures import ThreadPoolExecutor

from django.conf import settings
from django.core.management.base import BaseCommand

from api.models import Project
from api.utils.summary_cache import update_summary_cache


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

    def update_summaries(self, project_id, skip_test_project):
        update_summary_cache(project_id, skip_test_project=skip_test_project)

    def handle(self, *args, **options):
        is_forced = options["force"]
        skip_test_project = options["test_projects"] is not True

        if settings.ENVIRONMENT not in ("dev", "prod") and is_forced is False:
            print("Skipping update")
            return

        start_time = time()
        print("Updating summaries...")
        for project in Project.objects.all():
            self.update_summaries(project.pk, skip_test_project)
        # futures = []
        # with ThreadPoolExecutor(max_workers=1) as exc:
        #     futures.extend(
        #         exc.submit(self.update_summaries, project.pk, skip_test_project)
        #         for project in Project.objects.all()
        #     )

        # for future in futures:
        #     future.result()

        end_time = time()
        print(f"Done: {end_time - start_time:.3f}s")
