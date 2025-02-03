import logging
import os
import signal
import threading
from concurrent.futures import ThreadPoolExecutor

from django.core.management.base import BaseCommand

from api.models import SummaryCacheQueue
from api.utils.summary_cache import update_summary_cache

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    WAIT_SECONDS = 5
    stop_event = threading.Event()

    def _process_tasks(self, task):
        try:
            task.processing = True
            task.save()
            update_summary_cache(task.project_id)
            task.delete()
            return True
        except Exception:
            logger.exception(f"Error update_summary_cache [Project id: {task.project_id}]")
            task.processing = False
            task.attempts += 1
            task.save()
            return False

    def process_tasks(self, tasks):
        with ThreadPoolExecutor(max_workers=max(os.cpu_count(), 2)) as executor:
            executor.map(self._process_tasks, tasks)

    def handle(self, *args, **options):
        logger.info("Starting process_summaries")

        signal.signal(signal.SIGINT, self.handle_stop_signal)
        signal.signal(signal.SIGTERM, self.handle_stop_signal)

        while not self.stop_event.is_set():
            tasks = SummaryCacheQueue.objects.filter(attempts__lt=3).order_by("created_on")
            if not tasks.exists():
                self.stop_event.wait(self.WAIT_SECONDS)
            else:
                self.process_tasks(tasks)

    def handle_stop_signal(self, signum, frame):
        logger.info("Shutting down gracefully...")
        self.stop_event.set()
