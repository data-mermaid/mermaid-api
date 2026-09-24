from unittest.mock import MagicMock, patch

from django.db.utils import OperationalError
from django.urls import reverse

from api.models import CollectRecord
from api.submission.utils import (
    DEADLOCK_MAX_RETRIES,
    ERROR_STATUS,
    SUCCESS_STATUS,
    write_collect_record,
)
from api.submission.validations import OK
from api.submission.validations.validators import DrySubmitValidator
from api.utils import Testing

DEADLOCK_ERROR = OperationalError(
    "deadlock detected\nDETAIL: Process 1 waits for ShareLock on transaction 2; "
    'blocked by process 2.\nCONTEXT: while inserting index tuple in relation "revision"'
)


def _writer_mock(write_side_effect):
    writer = MagicMock()
    writer.write.side_effect = write_side_effect
    return writer


def test_writer_write_deadlock_is_retried_and_succeeds(valid_collect_record, profile1_request):
    """
    A deadlock raised while writer.write() saves observations/sample units
    (not just the collect_record.delete() step) must also be retried - this
    is the path write_collect_record's own `except Exception` used to
    silently swallow into an ERROR_STATUS result with no retry.
    """
    collect_record_id = valid_collect_record.id
    writer = _writer_mock([DEADLOCK_ERROR, None])

    with Testing(), patch("api.submission.utils.get_writer", return_value=writer), patch(
        "api.submission.utils.time.sleep"
    ):
        status, result = write_collect_record(valid_collect_record, profile1_request)

    assert writer.write.call_count == 2
    assert status == SUCCESS_STATUS
    assert result is None
    assert CollectRecord.objects.filter(id=collect_record_id).exists() is False


def test_writer_write_deadlock_exhausts_retries_and_reports_error(
    valid_collect_record, profile1_request
):
    collect_record_id = valid_collect_record.id
    writer = _writer_mock(DEADLOCK_ERROR)

    with Testing(), patch("api.submission.utils.get_writer", return_value=writer), patch(
        "api.submission.utils.time.sleep"
    ):
        status, result = write_collect_record(valid_collect_record, profile1_request)

    assert writer.write.call_count == DEADLOCK_MAX_RETRIES + 1
    assert status == ERROR_STATUS
    # transaction was rolled back each time - record is left intact
    assert CollectRecord.objects.filter(id=collect_record_id).exists() is True


def test_dry_submit_validator_retries_after_writer_write_deadlock(
    valid_collect_record, profile1_request
):
    """
    DrySubmitValidator calls write_collect_record(..., dry_run=True) directly,
    with no retry/exception handling of its own - it relies entirely on
    write_collect_record to absorb transient deadlocks.
    """
    writer = _writer_mock([DEADLOCK_ERROR, None])

    with Testing(), patch("api.submission.utils.get_writer", return_value=writer), patch(
        "api.submission.utils.time.sleep"
    ):
        validator = DrySubmitValidator()
        result = validator(valid_collect_record, request=profile1_request)

    assert writer.write.call_count == 2
    assert result.status == OK
    # dry run always rolls back, regardless of outcome
    assert CollectRecord.objects.filter(id=valid_collect_record.id).exists() is True


def test_non_deadlock_operational_error_is_not_retried(valid_collect_record, profile1_request):
    other_error = OperationalError("connection reset by peer")
    writer = _writer_mock(other_error)

    with Testing(), patch("api.submission.utils.get_writer", return_value=writer), patch(
        "api.submission.utils.time.sleep"
    ) as mock_sleep:
        status, result = write_collect_record(valid_collect_record, profile1_request)

    assert writer.write.call_count == 1
    assert mock_sleep.call_count == 0
    assert status == ERROR_STATUS


def test_submit_endpoint_reports_error_instead_of_500_under_persistent_deadlock(
    db_setup, api_client1, project1, collect_record4_with_v2_validation
):
    """
    Reproduces the shape of the production incident: POST .../collectrecords/submit/
    with a collect record whose write always deadlocks. Before this fix, the
    deadlock from collect_record.delete() (or, previously unretried, from
    writer.write()) propagated uncaught all the way to the view as a 500.
    """
    collect_record_id = str(collect_record4_with_v2_validation.pk)
    writer = _writer_mock(DEADLOCK_ERROR)
    url = reverse("collectrecords-submit", kwargs={"project_pk": str(project1.pk)})

    with patch("api.submission.utils.get_writer", return_value=writer), patch(
        "api.submission.utils.time.sleep"
    ):
        response = api_client1.post(
            url, data={"version": "2", "ids": [collect_record_id]}, format="json"
        )

    response_data = response.json()

    assert response.status_code == 200
    assert response_data[collect_record_id]["status"] == "error"
    assert CollectRecord.objects.filter(id=collect_record_id).exists() is True
