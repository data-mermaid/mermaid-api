from simpleq.workers import Worker


class _FakeJob:
    """A job double that records whether it ran, mirroring the subset of
    `simpleq.jobs.Job` that `Worker.work` touches. `fails` mimics a job whose
    handler raised, leaving `exception` set the way `simpleq.jobs.Job.run` would."""

    def __init__(self, name, visibility_timeout=None, fails=False):
        self.name = name
        self.visibility_timeout = visibility_timeout
        self.exception = None
        self.ran = False
        self._fails = fails

    def run(self):
        self.ran = True
        if self._fails:
            self.exception = Exception("simulated job failure")

    def __repr__(self):
        return f"<FakeJob {self.name}>"


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
