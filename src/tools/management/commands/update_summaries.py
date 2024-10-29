from time import time

from django.conf import settings
from django.core.management.base import BaseCommand

from api.models import Project
from api.utils.q import submit_job
from api.utils.summary_cache import update_summary_cache


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Ignores environment check before running update.",
        )
        parser.add_argument(
            "--skip_test_projects",
            action="store_true",
            help="Skips test projects when running update.",
        )

        parser.add_argument(
            "--project_id",
            help="Run for only project.",
        )

        parser.add_argument(
            "--foreground",
            action="store_true",
            help="Run in the foreground.",
        )

    def handle(self, *args, **options):
        is_forced = options["force"]
        skip_test_projects = options["skip_test_projects"] is True
        in_foreground = options["foreground"]
        project_id = options["project_id"]

        if settings.ENVIRONMENT not in ("dev", "prod") and is_forced is False:
            print("Skipping update")
            return

        start_time = time()
        print("Updating summaries...")

        projects = Project.objects.all()
        if project_id:
            projects = projects.filter(id=project_id)
            if not projects.exists():
                print(f"Project with id {project_id} not found")
                return

        for project in projects:
            if in_foreground:
                update_summary_cache(project_id=project.pk, skip_test_project=skip_test_projects)
            else:
                submit_job(
                    5,
                    True,
                    update_summary_cache,
                    project_id=project.pk,
                    skip_test_project=skip_test_projects,
                )

        end_time = time()
        print(f"Done: {end_time - start_time:.3f}s")
