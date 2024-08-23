from collections import defaultdict

from django.conf import settings
from django.core.management.base import BaseCommand

from simpleq import utils


class Command(BaseCommand):
    help = """SimpleQ Summary"""

    def __init__(self):
        super(Command, self).__init__()

    def add_arguments(self, parser):
        parser.add_argument("-n", dest="queue_name", default=False, help="Queue name")

    def handle(self, *args, **options):
        queue_name = options.get("queue_name") or getattr(settings, "QUEUE_NAME")
        if not queue_name:
            raise ValueError("Invalid queue_name")

        num_jobs = int(utils.num_jobs(queue_name))
        callable_summary = defaultdict(int)
        duplicates = defaultdict(int)

        jobs = utils.get_jobs(queue_name, num_jobs)
        try:
            for job in jobs:
                job_key = utils.key(job)
                callable_name = job.callable.__name__

                duplicates[job_key] += 1
                callable_summary[callable_name] += 1

            duplicates = {
                k: v
                for k, v in sorted(duplicates.items(), key=lambda item: item[1], reverse=True)
                if v > 1
            }

            print(f"*** Queue: {queue_name} ***")
            print("")

            if len(callable_summary) == 0:
                print("No jobs to summarize.")
            else:
                if len(duplicates.values()) == 0:
                    print("No duplicate jobs\n")
                else:
                    print("Duplicate Jobs")
                    print("--------------")
                    print("")
                    for job_key, val in duplicates.items():
                        if val == 1:
                            continue
                        print(f"{job_key}\t{val}")

                print("")
                print("Summary of Job Types")
                print("--------------------")
                print("")
                callable_summary = dict(sorted(callable_summary.items(), key=lambda item: item[1]))
                for job_key, val in callable_summary.items():
                    print(f"{job_key}\t{val}")

            print("\n-- // --\n")
        finally:
            for job in jobs:
                utils.release_job(job, queue_name)
