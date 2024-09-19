from datetime import datetime

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.autoreload import run_with_reloader

from simpleq.queues import Queue
from simpleq.workers import Worker


class Command(BaseCommand):
    help = """SimpleQ worker"""

    def __init__(self):
        super(Command, self).__init__()
    
    def handle(self, *args, **kwargs):
        run_with_reloader(self.run_worker)

    def add_arguments(self, parser):
        parser.add_argument("-n", dest="queue_name", default=False, help="Queue name")

    def run_worker(self, *args, **options):
        queue_name = options.get("queue_name") or getattr(settings, "QUEUE_NAME")
        if not queue_name:
            raise ValueError("Invalid queue_name")
        start_time = datetime.now()
        self.stdout.write(f"Worker start processing from {queue_name} queue, UTC time {start_time}")
        self.queue = Queue(queue_name)

        self.stdout.write("Running simpleq worker")
        self.worker = Worker(queues=[self.queue])
        self.worker.work()
        finish_time = datetime.now()
        runtime = (finish_time - start_time).total_seconds()
        self.stdout.write(
            f"Worker finished processing from {queue_name} queue, UTC time {finish_time}, total runtime {runtime}"
        )
    
    def handle(self, *args, **options):
        run_with_reloader(self.run_worker, *args, **options)
