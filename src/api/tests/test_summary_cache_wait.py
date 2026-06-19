import uuid
from unittest.mock import MagicMock, patch

import pytest

from api.models import SummaryCacheQueue
from api.utils.reports import create_sample_unit_method_summary_report
from api.utils.summary_cache import wait_for_summary_cache


def test_wait_skips_unrelated_projects_and_returns_false():
    """Only entries for the requested project_ids trigger a wait; others are ignored."""
    SummaryCacheQueue.objects.create(project_id=uuid.uuid4())

    with patch("api.utils.summary_cache.time") as mock_time:
        mock_time.monotonic.return_value = 0.0
        result = wait_for_summary_cache([uuid.uuid4()])

    assert result is False
    mock_time.sleep.assert_not_called()


def test_wait_polls_until_entry_cleared():
    project_id = uuid.uuid4()
    SummaryCacheQueue.objects.create(project_id=project_id)
    sleep_calls = [0]

    def fake_sleep(_):
        sleep_calls[0] += 1
        if sleep_calls[0] >= 2:
            SummaryCacheQueue.objects.filter(project_id=project_id).delete()

    with (
        patch("api.utils.summary_cache.SUMMARY_CACHE_MAX_WAIT", 30),
        patch("api.utils.summary_cache.time.sleep", side_effect=fake_sleep),
    ):
        result = wait_for_summary_cache([project_id])

    assert result is False


def test_wait_times_out_logs_warning_and_returns_true():
    project_id = uuid.uuid4()
    SummaryCacheQueue.objects.create(project_id=project_id)
    with (
        patch("api.utils.summary_cache.logger") as mock_logger,
        patch("api.utils.summary_cache.SUMMARY_CACHE_MAX_WAIT", -1),
    ):
        result = wait_for_summary_cache([project_id])
    assert result is True
    mock_logger.warning.assert_called_once()
    assert "Timed out" in mock_logger.warning.call_args[0][0]


@pytest.mark.parametrize("stale", [True, False])
def test_report_passes_stale_flag_to_email(project1, stale):
    mock_wb = MagicMock()
    with (
        patch("api.utils.reports.wait_for_summary_cache", return_value=stale),
        patch("api.utils.reports.create_protocol_report", return_value=mock_wb),
        patch("api.utils.reports.email_report") as mock_email,
    ):
        create_sample_unit_method_summary_report(
            project_ids=[project1.pk],
            protocol="fishbelt",
            send_email="test@example.com",
            request=MagicMock(user=MagicMock(profile=MagicMock(email="test@example.com"))),
            wait_for_cache=True,
        )
    assert mock_email.call_args.kwargs.get("data_may_be_stale") is stale
