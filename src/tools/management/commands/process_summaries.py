import os
from concurrent.futures import ThreadPoolExecutor
from time import sleep

from django.core.management.base import BaseCommand
from django.db import connection

from api.models import SummaryCacheQueue
from api.utils.summary_cache import update_summary_cache


class Command(BaseCommand):
    LOCK_ID = 8080
    WAIT_SECONDS = 5

    def acquire_lock(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_try_advisory_lock(%s);", [self.LOCK_ID])
            locked = cursor.fetchone()[0]
        return locked

    def release_lock(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_unlock(%s);", [self.LOCK_ID])

    def _process_tasks(self, task):
        try:
            task.processing = True
            task.save()
            update_summary_cache(task.project_id)
            task.delete()
            return True
        except Exception as e:
            print(f"Error update_summary_cache[Project id: {task.project_id}]: {e}")
            task.processing = False
            task.attempts += 1
            task.save()
            return False

    def process_tasks(self, tasks):
        with ThreadPoolExecutor(max_workers=min(os.cpu_count() - 1, 3)) as executor:
            executor.map(self._process_tasks, tasks)

    def handle(self, *args, **options):
        if not self.acquire_lock():
            print("Another process is already working on tasks.")
            return

        try:
            while True:
                tasks = SummaryCacheQueue.objects.filter(attempts__lt=3).order_by("created_on")
                if not tasks.exists():
                    sleep(self.WAIT_SECONDS)
                else:
                    self.process_tasks(tasks)

        finally:
            self.release_lock()
