import codecs
import uuid
from datetime import datetime
from pickle import dumps, loads


class Job:
    """An abstraction for a single unit of work (a job!)."""

    def __init__(self, job_id, group, callable, *args, **kwargs):
        """
        Create a new Job,

        :param obj callable: [optional] A callable to run.
        """
        self._id = job_id if job_id is not None else str(uuid.uuid4())
        self.group = group or "mermaid"
        self.start_time = None
        self.stop_time = None
        self.run_time = None
        self.exception = None
        self.result = None
        self.callable = callable
        self.args = args
        self.kwargs = kwargs
        self._sqs_message_id = None
        self._sqs_receipt_handle = None

    def __repr__(self):
        """Print a human-friendly object representation."""
        return f'<Job({{"callable": "{self.callable.__name__}"}})>'

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, val):
        self._id = val

    @property
    def composite_id(self):
        return f"{self.group}::{self.id}"

    @property
    def message(self):
        return dict(
            MessageAttributes={
                "id": {
                    "StringValue": self.id,
                    "DataType": "String"
                }
            },
            MessageDeduplicationId=self.composite_id,
            MessageGroupId=self.group,
            MessageBody=codecs.encode(
                dumps({
                    "callable": self.callable,
                    "args": self.args,
                    "kwargs": self.kwargs,
                }),
                "base64"
            ).decode()
        )

    @classmethod
    def from_message(cls, message):
        """
        Create a new Job, given a boto Message.

        :param obj message: The boto Message object to use.
        """
        data = loads(codecs.decode(message.body.encode(), "base64"))

        message_attributes = message.message_attributes or dict()
        group = (message.attributes or dict()).get("MessageGroupId")
        job_id = (message_attributes.get("id") or dict()).get("StringValue")

        job = cls(job_id, group, data["callable"], *data["args"], **data["kwargs"])
        job._sqs_message_id = message.message_id
        job._sqs_receipt_handle = message.receipt_handle

        return job

    def log(self, message):
        """
        Write the given message to standard out (STDOUT).
        """

        print(f"simpleq: {message}")

    def run(self):
        """Run this job."""
        self.start_time = datetime.utcnow()
        self.log(
            f"Starting job {self.callable.__name__} at {self.start_time.isoformat()}."
        )

        try:
            self.result = self.callable(*self.args, **self.kwargs)
        except Exception as e:
            self.exception = e

        if not self.exception:
            self.stop_time = datetime.utcnow()
            self.run_time = (self.stop_time - self.start_time).total_seconds()
            self.log(
                f"Finished job {self.callable.__name__} at {self.stop_time.isoformat()} in {self.run_time} seconds."
            )
        else:
            self.log(f"Job {self.callable.__name__} failed to run: {self.exception}")
