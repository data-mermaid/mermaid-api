import threading as th
from collections import defaultdict

import boto3
from django.conf import settings

from simpleq.jobs import Job


class Queue:
    """
    A representation of an Amazon SQS queue.

    There are two ways to create a Queue.

    1. Specify only a queue name, and connect to the default Amazon SQS region
       (*us-east-1*).  This will only work if you have your AWS credentials set
       appropriately in your environment (*``AWS_ACCESS_KEY_ID`` and
       ``AWS_SECRET_ACCESS_KEY``*).  To set your environment variables, you can
       use the shell command ``export``::

            $ export AWS_ACCESS_KEY_ID=xxx
            $ export AWS_SECRET_ACCESS_KEY=xxx

       You can then create a queue as follows:

            from simpleq.queues import Queue

            myqueue = Queue("myqueue")

    2. Specify a queue name and include an boto3 SQS resource:

            import boto3
            from simpleq.queues import Queue

            myqueue = Queue(
                "myqueue",
                sqs_resources=boto3.resource(
                    "sqs",
                    aws_access_key_id=aws_access_key,
                    aws_secret_access_key=aws_access_secret,
                    region_name=aws_region
                )
            )
    """

    BATCH_SIZE = getattr(settings, "SQS_BATCH_SIZE", 10)
    WAIT_SECONDS = getattr(settings, "SQS_WAIT_SECONDS", 20)
    SQS_MESSAGE_VISIBILITY = getattr(settings, "SQS_MESSAGE_VISIBILITY")
    USE_FIFO = True if getattr(settings, "USE_FIFO") == "True" else False
    _delayed_jobs = defaultdict(list)

    def __init__(self, name, sqs_resource=None):
        """
        Initialize an SQS queue.

        This will create a new boto SQS connection in the background, which will
        be used for all future queue requests.  This will speed up communication
        with SQS by taking advantage of boto's connection pooling functionality.

        :param str name: The name of the queue to use.
        :param obj sqs_resource: [optional] SQS Boto3 Resource.
        """
        self.name = name
        # Add type check
        if sqs_resource:
            self.sqs_resource = sqs_resource
        else:
            resource_args = {
                "service_name": "sqs",
                "aws_access_key_id": settings.AWS_ACCESS_KEY_ID,
                "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
                "region_name": settings.AWS_REGION,
            }
            if settings.ENDPOINT_URL:
                resource_args["endpoint_url"] = settings.ENDPOINT_URL

            self.sqs_resource = boto3.resource(**resource_args)

        self._queue = None

    def __repr__(self):
        """Print a human-friendly object representation."""
        return f'<Queue({"name": "{self.name}", "region": "{self.sqs_resource.region.name}"})>'

    @property
    def queue(self):
        """
        Return the underlying SQS queue object from boto.

        This will either lazily create (*or retrieve*) the queue from SQS by
        name.

        :returns: The SQS queue object.
        """
        if self._queue:
            return self._queue

        if self.USE_FIFO:
            queue_name = f"{self.name}.fifo"
        else:
            queue_name = self.name

        try:
            self._queue = self.sqs_resource.get_queue_by_name(QueueName=queue_name)
        except self.sqs_resource.meta.client.exceptions.QueueDoesNotExist:
            queue_attributes = {
                "VisibilityTimeout": str(self.SQS_MESSAGE_VISIBILITY),
                "FifoQueue": "false",
            }
            if self.USE_FIFO:
                queue_attributes["FifoQueue"] = "true"
                queue_attributes["ContentBasedDeduplication"] = "false"

            self._queue = self.sqs_resource.create_queue(
                QueueName=queue_name,
                Attributes=queue_attributes,
            )

        return self._queue

    def num_jobs(self):
        """
        Return the amount of jobs currently in this SQS queue.

        :rtype: int
        :returns: The amount of jobs currently in this SQS queue.
        """

        self.queue.load()
        attributes = self.queue.attributes or dict()
        return attributes.get("ApproximateNumberOfMessages")

    def delete(self):
        """
        Delete this SQS queue.

        This will remove all jobs in the queue, regardless of whether or not
        they're currently being processed.  This data cannot be recovered.
        """
        if self._queue:
            self._queue.delete()

    def add_job(self, job, delay=None):
        """
        Add a new job to the queue.

        This will serialize the desired code, and dump it into this SQS queue
        to be processed.

        :param obj job: The Job to enqueue.
        :param int delay: Delay sending job to SQS queue.

        """
        if delay:
            if job.id not in self._delayed_jobs:
                th.Timer(delay, self.add_job, args=[job]).start()

            self._delayed_jobs[job.id].append(job)
            return

        if job.id in self._delayed_jobs:
            del self._delayed_jobs[job.id]

        self.queue.send_message(**job.message)

    def remove_job(self, job):
        """
        Remove a job from the queue.

        :param obj job: The Job to dequeue.
        """
        if job._sqs_message_id is None or job._sqs_receipt_handle is None:
            print(f"Unable to remove job from sqs queue [{job}]")
            return

        self.queue.delete_messages(
            Entries=[
                dict(
                    Id=job._sqs_message_id,
                    ReceiptHandle=job._sqs_receipt_handle,
                )
            ]
        )

    def _cleanup_duplicate_jobs(self, duplicate_job_groups):
        for duplicate_jobs in duplicate_job_groups.values():
            for duplicate_job in duplicate_jobs:
                self.remove_job(duplicate_job)

    @property
    def jobs(self):
        """
        Iterate through all existing jobs in the cheapest and quickest possible
        way.

        By default we will:

            - Use the maximum batch size to reduce calls to SQS.  This will
              reduce the cost of running the service, as less requests equals
              less dollars.

            - Wait for as long as possible (*20 seconds*) for a message to be
              sent to us (*if none are in the queue already*).  This way, we'll
              reduce our total request count, and spend less dollars.

        .. note::
            This method is a generator which will continue to return results
            until this SQS queue is emptied.
        """

        messages = self.queue.receive_messages(
            AttributeNames=["All"],
            MaxNumberOfMessages=self.BATCH_SIZE,
            WaitTimeSeconds=self.WAIT_SECONDS,
            MessageAttributeNames=["id"],
        )
        duplicate_job_groups = {}

        for message in messages:
            job = Job.from_message(message)
            if job.id is not None and job.id in duplicate_job_groups:
                duplicate_job_groups[job.id].append(job)
                continue
            else:
                duplicate_job_groups[job.id] = []

            yield job

        self._cleanup_duplicate_jobs(duplicate_job_groups)
