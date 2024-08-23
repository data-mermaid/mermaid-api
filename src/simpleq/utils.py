import codecs
import itertools
from functools import cache, wraps
from pickle import dumps, loads

from django.conf import settings

from simpleq.queues import Queue


def init_queue(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "queue" not in kwargs or kwargs["queue"] is None:
            kwargs["queue"] = get_queue()
        return func(*args, **kwargs)
    return wrapper


@cache
def get_queue(queue_name=None, queue_url=None):
    q_name = queue_name or settings.QUEUE_NAME
    q = Queue(q_name, queue_url=queue_url)
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


def deserialize_key(job_key):
    # Decode the base64 encoded string to bytes
    decoded_bytes = codecs.decode(job_key, 'base64')
    
    # Deserialize the bytes back to the original object
    job_data = loads(decoded_bytes)
    job_data["callable"] = job_data["callable"].__name__
    
    return job_data


@init_queue
def get_jobs(num_jobs=100, queue=None):
    n = num_jobs // 10
    if num_jobs % 10 != 0:
        n += 1

    jobs = [list(queue.jobs) for _ in range(n)]
    return list(itertools.chain.from_iterable(jobs))


@init_queue
def num_jobs(queue=None):
    return queue.num_jobs()


@init_queue
def release_job(job, queue=None):
    queue.release_job(job)
