from datetime import datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.utils.autoreload import run_with_reloader

from api.checks import (
    ENFORCED_ENVIRONMENTS,
    check_inference_settings,
    ensure_pinned_classifier_registered,
)
from api.models.classification import ClassifierRegistrationError
from simpleq.queues import Queue
from simpleq.workers import Worker


class Command(BaseCommand):
    help = """SimpleQ worker"""

    def __init__(self):
        super().__init__()

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
        queue_name = options.get("queue_name") or getattr(settings, "QUEUE_NAME")
        # Only the image-processing queue's worker invokes the inference Lambda;
        # a misconfigured deploy fails here, on the run_from_argv path that can
        # exit the process, instead of hanging inside the reloader's daemon thread.
        if queue_name == settings.IMAGE_QUEUE_NAME:
            errors = check_inference_settings()
            if errors:
                raise CommandError("\n".join(str(error) for error in errors))
            # A crash-looping image worker trips the ECS circuit breaker, so a pinned
            # version that cannot be registered fails the deploy instead of every job.
            if settings.ENVIRONMENT in ENFORCED_ENVIRONMENTS:
                try:
                    ensure_pinned_classifier_registered()
                except ClassifierRegistrationError as e:
                    raise CommandError(str(e)) from e
                # run_with_reloader keeps this process alive as the reloader's
                # parent; an open connection here would idle for the task's lifetime.
                connection.close()
        run_with_reloader(self.run_worker, *args, **options)
