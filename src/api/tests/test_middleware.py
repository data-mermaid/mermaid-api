from unittest.mock import patch

from django.http import HttpResponse
from django.test import RequestFactory, override_settings

from api.middleware import HealthEndpointMiddleware, MetricsMiddleware


def test_health_endpoint_short_circuits():
    request = RequestFactory().get("/health/")

    def get_response(_request):
        raise AssertionError("get_response should not be called for /health/")

    response = HealthEndpointMiddleware(get_response=get_response)(request)

    assert response.status_code == 200
    assert response.content.startswith(b"OK")


def test_non_health_endpoint_passes_through():
    request = RequestFactory().get("/other/")
    sentinel = object()

    response = HealthEndpointMiddleware(get_response=lambda r: sentinel)(request)

    assert response is sentinel


def _logged_metrics_event(request):
    with (
        override_settings(DISABLE_METRICS=False, WRITE_METRICS_TO_DB=False),
        patch("api.middleware.DatabaseLogger"),
        patch("builtins.print") as mock_print,
    ):
        MetricsMiddleware(get_response=lambda r: HttpResponse())(request)
    mock_print.assert_called_once()
    _timestamp, event = mock_print.call_args.args
    return event


def test_metrics_record_user_agent_and_origin():
    request = RequestFactory().post(
        "/v1/projects/",
        HTTP_USER_AGENT="https://github.com/data-mermaid/mermaidr",
        HTTP_ORIGIN="https://app.datamermaid.org",
        HTTP_REFERER="https://app.datamermaid.org/projects",
    )

    event = _logged_metrics_event(request)

    assert event["user_agent"] == "https://github.com/data-mermaid/mermaidr"
    assert event["origin"] == "https://app.datamermaid.org"


def test_metrics_origin_falls_back_to_referer_and_truncates_user_agent():
    request = RequestFactory().get(
        "/v1/projects/",
        HTTP_USER_AGENT="x" * 1000,
        HTTP_REFERER="https://app.datamermaid.org/projects",
    )

    event = _logged_metrics_event(request)

    assert event["user_agent"] == "x" * 256
    assert event["origin"] == "https://app.datamermaid.org"


def test_metrics_origin_drops_referer_path_and_query():
    request = RequestFactory().get(
        "/v1/projects/",
        HTTP_REFERER="https://app.datamermaid.org/projects/abc/?access_token=secret&email=a@b.org",
    )

    event = _logged_metrics_event(request)

    assert event["origin"] == "https://app.datamermaid.org"
    assert "secret" not in str(event)
    assert "a@b.org" not in str(event)


def test_metrics_origin_ignores_unparseable_values():
    for value in ("null", "not a url", "http://[::1"):
        event = _logged_metrics_event(RequestFactory().get("/v1/projects/", HTTP_ORIGIN=value))
        assert event["origin"] == ""


def test_metrics_missing_headers_are_empty_strings():
    event = _logged_metrics_event(RequestFactory().get("/v1/projects/"))

    assert event["user_agent"] == ""
    assert event["origin"] == ""


def test_metrics_origin_drops_referer_credentials():
    request = RequestFactory().get(
        "/v1/projects/",
        HTTP_REFERER="https://alice:hunter2@app.datamermaid.org:8443/projects",
    )

    event = _logged_metrics_event(request)

    assert event["origin"] == "https://app.datamermaid.org:8443"
    assert "alice" not in str(event)
    assert "hunter2" not in str(event)


def test_metrics_origin_keeps_ipv6_brackets():
    event = _logged_metrics_event(
        RequestFactory().get("/v1/projects/", HTTP_ORIGIN="http://[::1]:8080")
    )

    assert event["origin"] == "http://[::1]:8080"
