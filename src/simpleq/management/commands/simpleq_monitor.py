import time
from sys import stdout

from django.conf import settings
from django.core.management.base import BaseCommand

from simpleq.queues import Queue


class Command(BaseCommand):
    help = """SimpleQ Monitor"""

    def __init__(self):
        super(Command, self).__init__()

    def add_arguments(self, parser):
        parser.add_argument("-n", dest="queue_name", default=False, help="Queue name")
        parser.add_argument("-s", dest="sleep_time", type=int, default=5, help="Number of seconds to sleep between queue calls.")

    def handle(self, *args, **options):
        sleep_time = options.get("sleep_time") or 5
        queue_name = options.get("queue_name") or getattr(settings, "QUEUE_NAME")
        if not queue_name:
            raise ValueError("Invalid queue_name")

        self.stdout.write(f"Monitoring {queue_name} queue")
        self.queue = Queue(queue_name)
        
        self.stdout.write("\n")
        while True:
            msg = f"\rNumber of jobs: {self.queue.num_jobs()}      "
            stdout.write(msg)
            time.sleep(sleep_time)
