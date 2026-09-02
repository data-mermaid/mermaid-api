import logging

import pytest

from api.utils.apikeys import AUDIT_LOGGER_NAME


@pytest.fixture
def api_key_audit_logs(caplog):
    """Capture the API key audit trail (C8).

    settings.LOGGING gives `api.apikeys` its own handler and propagate=False,
    so its records never reach the root logger caplog listens on. Attaching
    caplog's handler to that logger is what makes them visible to a test.
    """

    audit_logger = logging.getLogger(AUDIT_LOGGER_NAME)
    audit_logger.addHandler(caplog.handler)
    try:
        yield caplog
    finally:
        audit_logger.removeHandler(caplog.handler)


def api_key_audit_lines(caplog, tag):
    """The audit lines matching one `[apikey.<tag>]` marker."""

    marker = f"[apikey.{tag}]"
    return [record.getMessage() for record in caplog.records if marker in record.getMessage()]
