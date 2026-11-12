"""Gunicorn gthread worker using its supported thread-pool customization hook."""

import os

from gunicorn.workers.gthread import ThreadWorker

from app.worker_telemetry import InstrumentedThreadPool, WorkerTelemetry


class ObservableThreadWorker(ThreadWorker):
    def get_thread_pool(self):
        self.telemetry = None
        if os.environ.get("MERMAID_WORKER_TELEMETRY") != "1":
            return super().get_thread_pool()
        self.telemetry = WorkerTelemetry(self.cfg.threads)
        pool = InstrumentedThreadPool(self.cfg.threads, self.telemetry)
        self.telemetry.start()
        return pool

    def handle_request(self, *args, **kwargs):
        if self.telemetry is None:
            return super().handle_request(*args, **kwargs)
        self.telemetry.request_started()
        try:
            return super().handle_request(*args, **kwargs)
        finally:
            self.telemetry.request_finished()
