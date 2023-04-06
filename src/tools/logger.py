import queue
import threading

from .models import LogEvent


class DatabaseLogger:
    def __init__(self, chunk_size=1):
        self._chunk_size = chunk_size
        self._queue = queue.Queue()
        self._thread = threading.Thread(target=self._process_log_queue)
        self._thread.daemon = True
        self._thread.start()

    def write(self, timestamp, event):
        self._queue.put((timestamp, event))

    def _process_log_queue(self):
        while True:
            log_records = []
            for _ in range(self._chunk_size):
                try:
                    timestamp, event = self._queue.get(timeout=1)
                    log_records.append(LogEvent(
                        timestamp=timestamp,
                        event=event,
                    ))
                except queue.Empty:
                    break

            if log_records:
                LogEvent.objects.bulk_create(log_records)
