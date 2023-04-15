import atexit
import queue
import threading

from .models import LogEvent


class DatabaseLogger:
    def __init__(self, batch_size=1):
        self._batch_size = batch_size
        self._queue = queue.Queue()
        self._setup()

    def _setup(self):
        self._thread = threading.Thread(target=self._process_log_queue)
        self._thread.daemon = True
        self._thread.start()
        atexit.register(self._shutdown)

    def _shutdown(self):
        self._thread.join()
        self._queue = None

    def log(self, timestamp, event):
        if not self._thread.is_alive():
            self._setup()
        self._queue.put((timestamp, event))

    def _process_log_queue(self):
        while True:
            log_records = []
            for _ in range(self._batch_size):
                try:
                    timestamp, event = self._queue.get(timeout=1)
                    log_records.append(LogEvent(
                        timestamp=timestamp,
                        event=event,
                    ))
                except queue.Empty:
                    break

            if log_records:
                try:
                    LogEvent.objects.bulk_create(log_records)
                except Exception as e:
                    print(f"Error writing records to database: {e}")
                    print(log_records)
