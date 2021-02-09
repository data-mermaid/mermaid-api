from django.conf import settings
from django.core.management.base import BaseCommand

from simpleq.queues import Queue
from simpleq.workers import Worker


class Command(BaseCommand):
    help = """SimpleQ worker"""

    def __init__(self):
        super(Command, self).__init__()

    def add_arguments(self, parser):
        parser.add_argument("-n", dest="queue_name", default=False, help="Queue name")

    def handle(self, *args, **options):
        queue_name = options.get("queue_name") or getattr(settings, "QUEUE_NAME")
        if not queue_name:
            raise ValueError("Invalid queue_name")

        self.stdout.write(f"Listening to {queue_name} queue")
        self.queue = Queue(queue_name)

        self.stdout.write("Running simpleq worker")
        self.worker = Worker(queues=[self.queue])
        self.worker.work()
