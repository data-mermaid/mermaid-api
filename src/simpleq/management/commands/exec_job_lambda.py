import json

from django.core.management.base import BaseCommand

from simpleq.jobs import Job

# TODO configure logger and format


class Command(BaseCommand):
    help = """Lambda Job Executor"""

    def __init__(self):
        super(Command, self).__init__()

    def add_arguments(self, parser):
        parser.add_argument(
            "-m",
            dest="message",
            type=str,
            help="SQS message from lambda.",
        )

    def handle(self, *args, **options):
        message = options.get("message")
        print(json.dumps(message))

        job = Job.from_message(message)
        job.run()
