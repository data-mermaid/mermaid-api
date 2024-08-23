import codecs
import itertools
from functools import cache
from pickle import dumps

from django.conf import settings

from simpleq.queues import Queue


@cache
def _queue(queue_name=None):
    q_name = queue_name or settings.QUEUE_NAME
    q = Queue(q_name)
    q.WAIT_SECONDS = 0

    return q


def key(job):
    return codecs.encode(
        dumps(
            {
                "callable": job.callable,
                "args": job.args,
                "kwargs": job.kwargs,
            }
        ),
        "base64",
    )


def get_jobs(queue_name, num_jobs=100):
    if num_jobs % 10 != 0:
        num_jobs = ((num_jobs // 10) + 1) * 10

    q = _queue(queue_name)
    jobs = [list(q.jobs) for _ in range(num_jobs)]
    return list(itertools.chain.from_iterable(jobs))


def num_jobs(queue_name=None):
    q = _queue(queue_name=queue_name)
    return q.num_jobs()


def release_job(job, queue_name=None):
    q = _queue(queue_name=queue_name)
    q.release_job(job)
