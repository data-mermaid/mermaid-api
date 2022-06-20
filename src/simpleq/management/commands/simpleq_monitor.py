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

    def handle(self, *args, **options):
        queue_name = options.get("queue_name") or getattr(settings, "QUEUE_NAME")
        if not queue_name:
            raise ValueError("Invalid queue_name")

        self.stdout.write(f"Monitoring {queue_name} queue")
        self.queue = Queue(queue_name)
        
        self.stdout.write("\n")
        prev_msg = ""
        while True:
            msg = f"\r {' ' * len(prev_msg) }\rNumber of jobs: {self.queue.num_jobs()}"
            stdout.write(msg)
            prev_msg = msg
            time.sleep(5)
