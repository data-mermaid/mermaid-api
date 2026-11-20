"""Sample worker occupancy to CloudWatch EMF without changing request handling."""

import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.request import urlopen


def task_identity():
    identity = {
        "ServiceName": os.environ.get("OTEL_SERVICE_NAME", "api"),
        "ClusterName": "unknown",
        "TaskId": "unknown",
    }
    uri = os.environ.get("ECS_CONTAINER_METADATA_URI_V4", "")
    if not uri.startswith("http://169.254.170.2/"):
        return identity
    try:
        with urlopen(f"{uri}/task", timeout=0.5) as response:
            task = json.load(response)
        identity.update(
            ClusterName=task.get("Cluster", "unknown").split("/")[-1],
            TaskId=task.get("TaskARN", "unknown").split("/")[-1],
        )
    except (OSError, ValueError, TypeError, AttributeError):
        pass  # A metadata outage must not prevent the worker from starting.
    return identity


def emit(record):
    try:
        print(json.dumps(record, separators=(",", ":")), flush=True)
    except (OSError, ValueError):
        pass  # Telemetry cannot fail application requests.


class WorkerTelemetry:
    def __init__(self, capacity, identity=None, emit_record=emit):
        self.capacity = capacity
        self.identity = task_identity() if identity is None else identity
        self.emit_record = emit_record
        self.lock = threading.Lock()
        self.busy = self.queued = self.requests = self.completed = 0
        self.queue_wait_max_ms = 0.0
        self.stopped = threading.Event()

    def request_started(self):
        with self.lock:
            self.requests += 1

    def request_finished(self):
        with self.lock:
            self.requests -= 1

    def snapshot(self):
        timestamp = int(time.time() * 1000)
        with self.lock:
            values = {
                "BusyThreads": self.busy,
                "ThreadCapacity": self.capacity,
                "QueuedConnections": self.queued,
                "ActiveRequests": self.requests,
                "QueueWaitMaxMs": self.queue_wait_max_ms,
                "CompletedConnections": self.completed,
            }
            self.queue_wait_max_ms = 0.0
            self.completed = 0
        return {
            "Type": "WorkerTelemetry",
            "Timestamp": timestamp,
            **self.identity,
            "WorkerPid": str(os.getpid()),
            **values,
            "_aws": {
                "Timestamp": timestamp,
                "CloudWatchMetrics": [
                    {
                        "Namespace": "Mermaid/Workers",
                        "Dimensions": [["ClusterName", "ServiceName", "TaskId", "WorkerPid"]],
                        "Metrics": [
                            {
                                "Name": name,
                                "Unit": "Milliseconds" if name == "QueueWaitMaxMs" else "Count",
                            }
                            for name in values
                        ],
                    }
                ],
            },
        }

    def publish(self):
        try:
            self.emit_record(self.snapshot())
        except Exception:
            pass  # Custom/test emitters have the same fail-open contract.

    def start(self, interval=10):
        def sample():
            while not self.stopped.wait(interval):
                self.publish()

        threading.Thread(target=sample, name="worker-telemetry", daemon=True).start()

    def stop(self):
        self.stopped.set()
        self.publish()


class InstrumentedThreadPool(ThreadPoolExecutor):
    """Measure connection jobs queued through the public Executor.submit API."""

    def __init__(self, max_workers, telemetry):
        super().__init__(max_workers=max_workers)
        self.telemetry = telemetry

    def submit(self, fn, /, *args, **kwargs):
        telemetry = self.telemetry
        queued_at = time.monotonic()
        with telemetry.lock:
            telemetry.queued += 1

        def run():
            with telemetry.lock:
                telemetry.queued -= 1
                telemetry.busy += 1
                telemetry.queue_wait_max_ms = max(
                    telemetry.queue_wait_max_ms, (time.monotonic() - queued_at) * 1000
                )
            try:
                return fn(*args, **kwargs)
            finally:
                with telemetry.lock:
                    telemetry.busy -= 1
                    telemetry.completed += 1

        try:
            future = super().submit(run)
        except Exception:
            with telemetry.lock:
                telemetry.queued -= 1
            raise

        def cancelled(done):
            if done.cancelled():
                with telemetry.lock:
                    telemetry.queued -= 1

        future.add_done_callback(cancelled)
        return future

    def shutdown(self, wait=True, *, cancel_futures=False):
        try:
            return super().shutdown(wait=wait, cancel_futures=cancel_futures)
        finally:
            self.telemetry.stop()
