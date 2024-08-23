from collections import defaultdict

from django.conf import settings
from django.core.management.base import BaseCommand

from simpleq import utils


class Command(BaseCommand):
    help = """SimpleQ Summary"""

    def __init__(self):
        super(Command, self).__init__()

    def add_arguments(self, parser):
        parser.add_argument("-n", dest="queue_name", default=None, help="Queue name")
        parser.add_argument("--queue_url", dest="queue_url", default=None, help="Queue url")


    def handle(self, *args, **options):
        verbosity = options.get("verbosity") or 0
        queue_name = options.get("queue_name") or getattr(settings, "QUEUE_NAME")
        queue_url = options.get("queue_url")

        if not queue_name:
            raise ValueError("Invalid queue_name")

        queue = utils.get_queue(queue_name=queue_name, queue_url=queue_url)

        num_jobs = int(utils.num_jobs(queue=queue))
        callable_summary = defaultdict(int)
        duplicates = {}

        if verbosity > 1:
            self.stdout.write("INFO: fetching jobs\n")

        jobs = utils.get_jobs(num_jobs, queue=queue)

        if verbosity > 1:
            self.stdout.write("INFO: summarizing jobs...\n")
        try:
            for job in jobs:
                job_key = utils.key(job)
                callable_name = job.callable.__name__

                if job_key not in duplicates:
                    duplicates[job_key] = 0
                else:
                    duplicates[job_key] += 1
                callable_summary[callable_name] += 1

            duplicates = {
                k: v
                for k, v in sorted(duplicates.items(), key=lambda item: item[1], reverse=True)
                if v > 1
            }

            self.stdout.write(f"\n\n*** Queue: {queue_name} ***\n\n")

            if len(callable_summary) == 0:
                self.stdout.write("No jobs to summarize.\n")
            else:
                if len(duplicates.values()) == 0:
                    self.stdout.write("No duplicate jobs\n")
                else:
                    self.stdout.write("Duplicate Jobs\n")
                    self.stdout.write("--------------\n")
                    self.stdout.write("\n")
                    for job_key, val in duplicates.items():
                        if val == 1:
                            continue
                        self.stdout.write(f"{utils.deserialize_key(job_key)}\t{val}")

                self.stdout.write("\n")
                self.stdout.write("Summary of Job Types\n")
                self.stdout.write("--------------------\n")
                self.stdout.write("\n")
                callable_summary = dict(sorted(callable_summary.items(), key=lambda item: item[1]))
                for job_key, val in callable_summary.items():
                    self.stdout.write(f"{job_key}\t{val}\n")

            self.stdout.write("\n-- // --\n\n")
        finally:
            if verbosity > 1:
                self.stdout.write("INFO: putting jobs back on queue\n")
            for job in jobs:
                try:
                    utils.release_job(job, queue=queue)
                except Exception as e:
                    self.stdout.write(f"WARNING: skipping relase job {e}\n")
                    # Skip if there's an issue
                    pass
