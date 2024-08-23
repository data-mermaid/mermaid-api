from collections import defaultdict

from django.conf import settings
from django.core.management.base import BaseCommand

from simpleq import utils


class Command(BaseCommand):
    help = """SimpleQ Deduplicate"""

    def __init__(self):
        super(Command, self).__init__()

    def add_arguments(self, parser):
        parser.add_argument("-n", "--queue-name", dest="queue_name", default=None, help="Queue name")
        parser.add_argument("--queue-url", dest="queue_url", default=None, help="Queue url")
        parser.add_argument("--dry-run", action="store_true", help="Only print out number of duplicates")

    def handle(self, *args, **options):
        queue_name = options.get("queue_name") or getattr(settings, "QUEUE_NAME")
        queue_url = options.get("queue_url")
        is_dry_run = options.get("dry_run")

        if not queue_name:
            raise ValueError("Invalid queue_name")

        queue = utils.get_queue(queue_name=queue_name, queue_url=queue_url)

        num_jobs = int(utils.num_jobs(queue=queue))
        jobs = utils.get_jobs(num_jobs=num_jobs, queue=queue)

        duplicates = {}
        jobs_to_release = []
        try:
            self.stdout.write(f"Checking queue '{queue_name}' for duplicates.\n")
            self.stdout.write(f"Total number of jobs: {num_jobs}\n")
            for job in jobs:
                job_key = utils.key(job)
                if job_key not in duplicates:
                    duplicates[job_key] = 0
                    jobs_to_release.append(job)
                else:
                    duplicates[job_key] += 1
                    if is_dry_run is False:
                        queue.remove_job(job)
                    else:
                        jobs_to_release.append(job)

            duplicates = {k: v for k, v in duplicates.items() if v > 0}
            num_duplicates = sum([v for v in duplicates.values() if v > 0])
            if is_dry_run:
                self.stdout.write(f"Number of duplicate jobs: {num_duplicates}\n")
            else:
                self.stdout.write(f"Number of duplicate jobs removed: {num_duplicates}\n")

        finally:
            for job in jobs_to_release:
                try:
                    utils.release_job(job, queue=queue)
                except Exception as e:
                    self.stdout.write(f"WARNING: skipping relase job {e}\n")
                    # Skip if there's an issue
                    pass
