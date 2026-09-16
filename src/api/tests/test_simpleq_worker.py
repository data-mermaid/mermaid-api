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


def test_extend_visibility_failure_does_not_stop_the_batch(db_setup, caplog):
    jobs = [
        _FakeJob("first", visibility_timeout=30),
        _FakeJob("second", visibility_timeout=30),
        _FakeJob("third", visibility_timeout=30, fails=True),
    ]
    queue = _FailingVisibilityQueue(jobs)
    worker = Worker([queue])

    worker.work(burst=True)

    assert [job.ran for job in jobs] == [True, True, True]
    assert queue.removed == jobs[:2]
    assert jobs[2] not in queue.removed
    assert "[classify.processing_error]" in caplog.text
