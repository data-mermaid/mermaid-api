import io
import json

import pytest
from botocore.exceptions import ClientError, ReadTimeoutError
from django.test import override_settings

from api.utils import inference
from api.utils.inference import InferenceError, invoke_pyspacer


class _FakeClient:
    def __init__(self, *, payload=None, function_error=None, raise_error=None):
        self._payload = payload if payload is not None else {}
        self._function_error = function_error
        self._raise_error = raise_error
        self.calls = []

    def invoke(self, **kwargs):
        self.calls.append(kwargs)
        if self._raise_error is not None:
            raise self._raise_error
        resp = {"Payload": io.BytesIO(json.dumps(self._payload).encode("utf-8"))}
        if self._function_error:
            resp["FunctionError"] = self._function_error
        return resp


@override_settings(INFERENCE_LAMBDA_PYSPACER="dev-mermaid-inference-pyspacer")
def test_invoke_returns_parsed_payload(monkeypatch):
    fake = _FakeClient(payload={"point_results": []})
    monkeypatch.setattr(inference, "get_lambda_client", lambda *a, **k: fake)

    out = invoke_pyspacer({"classifier_type": "pyspacer"})

    assert out == {"point_results": []}
    assert fake.calls[0]["FunctionName"] == "dev-mermaid-inference-pyspacer"
    assert fake.calls[0]["InvocationType"] == "RequestResponse"


@override_settings(INFERENCE_LAMBDA_PYSPACER="dev-mermaid-inference-pyspacer")
def test_invoke_raises_on_function_error(monkeypatch):
    fake = _FakeClient(payload={"errorMessage": "boom"}, function_error="Unhandled")
    monkeypatch.setattr(inference, "get_lambda_client", lambda *a, **k: fake)

    with pytest.raises(InferenceError):
        invoke_pyspacer({"classifier_type": "pyspacer"})


@override_settings(INFERENCE_LAMBDA_PYSPACER="dev-mermaid-inference-pyspacer")
def test_invoke_wraps_client_error_as_inference_error(monkeypatch):
    error = ClientError(
        {"Error": {"Code": "TooManyRequestsException", "Message": "throttled"}}, "Invoke"
    )
    fake = _FakeClient(raise_error=error)
    monkeypatch.setattr(inference, "get_lambda_client", lambda *a, **k: fake)

    with pytest.raises(InferenceError) as exc:
        invoke_pyspacer({"classifier_type": "pyspacer"})

    assert "invoke_pyspacer" in str(exc.value)
    assert "TooManyRequestsException" in str(exc.value)


@override_settings(INFERENCE_LAMBDA_PYSPACER="dev-mermaid-inference-pyspacer")
def test_lambda_client_read_timeout_outlives_function_timeout(monkeypatch):
    captured = {}

    class _FakeSession:
        def __init__(self, **kwargs):
            pass

        def client(self, service_name, config=None):
            captured["service_name"] = service_name
            captured["config"] = config
            return object()

    # A cleared cache guarantees this call reaches Session regardless of what
    # earlier tests left cached.
    monkeypatch.setattr(inference, "_lambda_client", None)
    monkeypatch.setattr(inference, "Session", _FakeSession)

    inference.get_lambda_client()

    assert captured["service_name"] == "lambda"
    config = captured["config"]
    # Hand-derived from the Lambda's own 10-minute timeout: botocore's 60s default
    # would abort a synchronous invoke before a slow function itself times out.
    assert config.read_timeout >= 600


@override_settings(
    INFERENCE_LAMBDA_PYSPACER="dev-mermaid-inference-pyspacer",
    AWS_ACCESS_KEY_ID="testing",
    AWS_SECRET_ACCESS_KEY="testing",
    AWS_REGION="us-east-1",
)
def test_invoke_pyspacer_retries_up_to_the_configured_ceiling_and_no_further(monkeypatch):
    """A real boto3 Lambda client, with only its HTTP transport faked, retries a
    read-timeout up to its configured attempt ceiling and then stops."""
    # Rebuild the client under the credentials set above so request signing succeeds
    # and the call reaches the faked transport instead of failing before it.
    monkeypatch.setattr(inference, "_lambda_client", None)
    client = inference.get_lambda_client()
    # botocore's Config(retries={"max_attempts": N}) means N retries after the
    # initial request; total_max_attempts is the real total the client enforces.
    expected_attempts = client.meta.config.retries["total_max_attempts"]
    # Hand-derived from the 1500s visibility timeout budget (see
    # INFERENCE_JOB_VISIBILITY_TIMEOUT): 1 retry configured, so 2 total invokes.
    # Pinning this literal, rather than only comparing against itself below,
    # is what catches the ceiling silently drifting back up.
    assert expected_attempts == 2

    calls = []

    def fake_send(request):
        calls.append(request)
        raise ReadTimeoutError(endpoint_url=request.url)

    monkeypatch.setattr(client._endpoint.http_session, "send", fake_send)

    with pytest.raises(InferenceError):
        invoke_pyspacer({"classifier_type": "pyspacer"})

    assert len(calls) == expected_attempts
