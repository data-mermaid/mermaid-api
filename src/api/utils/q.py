import codecs
import hashlib
import math
import time
from pickle import dumps

from django.conf import settings

from simpleq.jobs import Job
from simpleq.queues import Queue


def submit_job(delay, callable, *args, **kwargs):
    args = args or []
    kwargs = kwargs or []
    q = Queue(settings.QUEUE_NAME)
    job_id = generate_job_id(delay, callable, *args, **kwargs)
    job = Job(job_id, None, callable, *args, **kwargs)
    q.add_job(job, delay=delay)

    return job_id


def generate_job_id(delay, *args, **kwargs):
    timestamp = ""
    if delay > 0:
        t = int(time.time())
        _delay = float(delay)
        timestamp = math.ceil(t / _delay) * _delay

    pickled_fx = codecs.encode(
        dumps(
            {
                "timestamp": timestamp,
                "callable": callable,
                "args": args,
                "kwargs": kwargs,
            }
        ),
        "base64",
    )
    return hashlib.sha1(pickled_fx).hexdigest()
