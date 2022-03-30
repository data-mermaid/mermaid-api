import uuid
from time import sleep

from simpleq.jobs import Job
from simpleq.queues import Queue


def log_stuff(txt):
    print(txt)


def run():
    q = None
    try:
        job_id = str(uuid.uuid4())
        uid = str(uuid.uuid4())
        print("Creating queue")
        q = Queue("simpleq_test")
        job = Job(job_id, None, log_stuff, uid)
        print(f"job_id: {job_id}")
        print(f"uid: {uid}")

        for _ in range(10):
            q.add_job(job, delay=5)

        sleep(10)
        print(f"q.num_jobs(): {q.num_jobs()}")

    finally:
        if q:
            q.delete()
