import logging
from datetime import datetime
from time import sleep

logger = logging.getLogger(__name__)


class Worker:
    """
    A simple queue worker.

    This worker listens to one or more queues for jobs, then executes each job
    to complete the work.
    """

    def __init__(self, queues, concurrency=10):
        """
        Initialize a new worker.

        :param list queues: A list of queues to monitor.
        :param int concurrency: The amount of jobs to process concurrently.
            Depending on what type of concurrency is in use (*either gevent, or
            multiprocessing*), this may correlate to either green threads or
            CPU processes, respectively.
        """
        self.queues = queues
        self.concurrency = concurrency

    def __repr__(self):
        """Print a human-friendly object representation."""
        return f'<Worker({"queues": {self.queues!r}})>'

    def work(self, burst=False, wait_seconds=5):
        """
        Monitor all queues and execute jobs.

        Once started, this will run forever (*unless the burst option is
        True*).

        :param bool burst: Should we quickly *burst* and finish all existing
            jobs then quit?
        """

        while True:
            start_time = datetime.now()
            logger.info(f"Fetching message(s), starting UTC time {start_time}\n")
            for queue in self.queues:
                for job in queue.jobs:
                    if job.visibility_timeout:
                        try:
                            queue.extend_job_visibility(job, job.visibility_timeout)
                        except Exception as e:
                            # A failed extension usually means the receipt handle is
                            # already dead; skip so the message redelivers instead of
                            # risking a second, costly inference call mid-run.
                            logger.exception(
                                f"[classify.processing_error] failed to extend visibility for job {job}, skipping it this cycle: {e}"
                            )
                            continue
                    job.run()
                    if not job.exception:
                        queue.remove_job(job)
            finish_time = datetime.now()
            runtime = (finish_time - start_time).total_seconds()
            logger.info(
                f"Finished Processing message(s), UTC time {start_time}, total runtime {runtime}\n"
            )

            if burst:
                break

            sleep(wait_seconds)
