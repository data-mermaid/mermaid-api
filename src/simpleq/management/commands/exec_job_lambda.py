import os

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = """Lambda Job Executor"""

    def __init__(self):
        super(Command, self).__init__()

    def add_arguments(self, parser):
        parser.add_argument(
            "-s",
            dest="sleep_time",
            type=int,
            default=0,
            help="Number of seconds to sleep between queue calls.",
        )

    def handle(self, *args, **options):
        # sleep_time = options.get("sleep_time")
        print("LAMBDA -> EXEC")
        print(os.environ["DB_PASSWORD"])
        print(os.environ["SECRET_KEY"])
