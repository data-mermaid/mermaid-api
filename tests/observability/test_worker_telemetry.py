import threading

import pytest

from app.worker_telemetry import InstrumentedThreadPool, WorkerTelemetry


def test_busy_worker_queue_wait_and_completion_are_measured():
    telemetry = WorkerTelemetry(1, identity={"TaskId": "test"}, emit_record=lambda record: None)
    release, started = threading.Event(), threading.Event()

    def busy():
        started.set()
        assert release.wait(2)

    with InstrumentedThreadPool(1, telemetry) as pool:
        first = pool.submit(busy)
        assert started.wait(2)
        second = pool.submit(lambda: 42)
        sample = telemetry.snapshot()
        assert sample["BusyThreads"] == 1
        assert sample["QueuedConnections"] == 1
        assert sample["ThreadCapacity"] == 1
        release.set()
        first.result(timeout=2)
        assert second.result(timeout=2) == 42
        sample = telemetry.snapshot()
        assert sample["BusyThreads"] == sample["QueuedConnections"] == 0
        assert sample["CompletedConnections"] == 2
        assert sample["QueueWaitMaxMs"] > 0
        assert telemetry.snapshot()["CompletedConnections"] == 0


def test_cancelled_and_failed_jobs_do_not_leak_occupancy():
    telemetry = WorkerTelemetry(1, identity={}, emit_record=lambda record: None)
    release, started = threading.Event(), threading.Event()

    def busy():
        started.set()
        assert release.wait(2)

    with InstrumentedThreadPool(1, telemetry) as pool:
        first = pool.submit(busy)
        assert started.wait(2)
        cancelled = pool.submit(lambda: None)
        assert cancelled.cancel()
        assert telemetry.snapshot()["QueuedConnections"] == 0
        release.set()
        first.result(timeout=2)

        def fail():
            raise RuntimeError("job failed")

        with pytest.raises(RuntimeError, match="job failed"):
            pool.submit(fail).result(timeout=2)
        assert telemetry.snapshot()["BusyThreads"] == 0
    with pytest.raises(RuntimeError):
        pool.submit(lambda: None)
    assert telemetry.snapshot()["QueuedConnections"] == 0


def test_request_cleanup_and_telemetry_failure_do_not_mask_application_error(monkeypatch):
    from app.gunicorn_worker import ObservableThreadWorker, ThreadWorker

    telemetry = WorkerTelemetry(
        4,
        identity={},
        emit_record=lambda record: (_ for _ in ()).throw(OSError("logs unavailable")),
    )
    worker = object.__new__(ObservableThreadWorker)
    worker.telemetry = telemetry

    def fail(*args, **kwargs):
        assert telemetry.snapshot()["ActiveRequests"] == 1
        raise RuntimeError("request failed")

    monkeypatch.setattr(ThreadWorker, "handle_request", fail)
    with pytest.raises(RuntimeError, match="request failed"):
        worker.handle_request(None, None)
    assert telemetry.snapshot()["ActiveRequests"] == 0
    telemetry.publish()


def test_telemetry_disabled_keeps_standard_worker_pool(monkeypatch):
    from types import SimpleNamespace

    from app.gunicorn_worker import ObservableThreadWorker

    monkeypatch.delenv("MERMAID_WORKER_TELEMETRY", raising=False)
    worker = object.__new__(ObservableThreadWorker)
    worker.cfg = SimpleNamespace(threads=2)
    with worker.get_thread_pool() as pool:
        assert pool.submit(lambda: "ok").result() == "ok"
        assert not isinstance(pool, InstrumentedThreadPool)
