"""
Regression tests for Trello card 2252.

A SimpleQ job body is a pickle, and Job.from_message unpickles it, which runs
arbitrary code. The body is now HMAC-signed with the Django SECRET_KEY on enqueue
and verified on dequeue, so a forged or tampered SQS message is refused before the
unpickle step.
"""

from types import SimpleNamespace

import pytest

from simpleq.jobs import Job


def sample_callable(*args, **kwargs):  # module-level so it is picklable
    return "ok"


def _received(message_dict):
    """Build a boto-like received message from Job.message output."""
    return SimpleNamespace(
        body=message_dict["MessageBody"],
        message_attributes=message_dict["MessageAttributes"],
        attributes={},
        message_id="m1",
        receipt_handle="r1",
    )


def test_signed_message_round_trips():
    job = Job(None, "mermaid", False, sample_callable, 1, two=2)
    received = _received(job.message)
    rebuilt = Job.from_message(received)
    assert rebuilt.callable is sample_callable
    assert rebuilt.args == (1,)
    assert rebuilt.kwargs == {"two": 2}


def test_missing_signature_is_rejected():
    job = Job(None, "mermaid", False, sample_callable)
    received = _received(job.message)
    del received.message_attributes["sig"]
    with pytest.raises(ValueError):
        Job.from_message(received)


def test_tampered_body_is_rejected():
    job = Job(None, "mermaid", False, sample_callable)
    message = job.message
    # Keep the old (valid) signature but swap the body for a different payload.
    forged = Job(None, "mermaid", False, sample_callable, "attacker").message
    message["MessageBody"] = forged["MessageBody"]
    with pytest.raises(ValueError):
        Job.from_message(_received(message))
