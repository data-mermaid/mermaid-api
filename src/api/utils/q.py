import uuid

from django.conf import settings

from simpleq.jobs import Job
from simpleq.queues import Queue


def submit_job(callable, *args, **kwargs):
    args = args or []
    kwargs = kwargs or []
    q = Queue(settings.QUEUE_NAME)
    job = Job(
        None,
        None,
        callable,
        *args,
        **kwargs
    )
    q.add_job(job, delay=1)

    return job.id
