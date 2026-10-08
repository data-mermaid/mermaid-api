from unittest.mock import patch

import pytest

from simpleq.workers import Worker


@pytest.fixture(autouse=True)
def close_old_connections():
    # Closing the real connection inside pytest-django's test transaction breaks teardown.
    with patch("simpleq.workers.close_old_connections") as mock:
        yield mock


class _FakeJob:
    """A job double that records whether it ran, mirroring the subset of
    `simpleq.jobs.Job` that `Worker.work` touches. `fails` mimics a job whose
    handler raised, leaving `exception` set the way `simpleq.jobs.Job.run` would."""

    def __init__(self, name, visibility_timeout=None, fails=False, events=None):
        self.name = name
        self.events = events
        self.visibility_timeout = visibility_timeout
        self.exception = None
        self.ran = False
        self._fails = fails

    def run(self):
        self.ran = True
        if self.events is not None:
            self.events.append(f"run {self.name}")
        if self._fails:
            self.exception = Exception("simulated job failure")

    def __repr__(self):
        return f"<FakeJob {self.name}>"


class _Queue:
    """A queue double whose visibility extensions always succeed."""

    def __init__(self, jobs):
        self._jobs = jobs
        self.removed = []

    @property
    def jobs(self):
        return iter(self._jobs)

    def extend_job_visibility(self, job, timeout):
        pass

    def remove_job(self, job):
        self.removed.append(job)


class _FailingVisibilityQueue:
    """A queue double whose `extend_job_visibility` always raises, mirroring an
    expired or already-redelivered SQS receipt handle."""

    def __init__(self, jobs):
        self._jobs = jobs
        self.removed = []

    @property
    def jobs(self):
        return iter(self._jobs)

    def extend_job_visibility(self, job, timeout):
        raise Exception("simulated visibility extension failure")

    def remove_job(self, job):
        self.removed.append(job)


def test_failed_visibility_extension_skips_the_job_but_not_the_batch(db_setup, caplog):
    needs_extension = _FakeJob("needs_extension", visibility_timeout=30)
    no_timeout = _FakeJob("no_timeout", visibility_timeout=None)
    queue = _FailingVisibilityQueue([needs_extension, no_timeout])
    worker = Worker([queue])

    worker.work(burst=True)

    assert needs_extension.ran is False
    assert needs_extension not in queue.removed
    assert no_timeout.ran is True
    assert no_timeout in queue.removed
    assert "[classify.processing_error]" in caplog.text


def test_db_connections_are_recycled_around_each_job(close_old_connections):
    events = []
    close_old_connections.side_effect = lambda: events.append("close")
    first = _FakeJob("first", visibility_timeout=30, events=events)
    second = _FakeJob("second", events=events)
    queue = _Queue([first, second])

    Worker([queue]).work(burst=True)

    assert events == ["close", "run first", "close", "close", "run second", "close"]
    assert queue.removed == [first, second]


def test_db_connections_are_recycled_after_a_failed_job(close_old_connections):
    events = []
    close_old_connections.side_effect = lambda: events.append("close")
    failing = _FakeJob("failing", fails=True, events=events)
    queue = _Queue([failing])

    Worker([queue]).work(burst=True)

    assert events == ["close", "run failing", "close"]
    assert queue.removed == []
