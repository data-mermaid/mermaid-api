import io
import json

import pytest
from botocore.exceptions import (
    ClientError,
    ConnectionClosedError,
    IncompleteReadError,
    ReadTimeoutError,
    ResponseStreamingError,
)
from django.test import override_settings

from api.utils import inference
from api.utils.inference import InferenceError, invoke_pyspacer


class _RaisingPayload:
    """Stand-in for response["Payload"] whose .read() itself raises, e.g. the
    StreamingBody timeout/streaming errors botocore can surface after invoke()
    already returned successfully."""

    def __init__(self, error):
        self._error = error

    def read(self):
        raise self._error


class _FakeClient:
    def __init__(
        self, *, payload=None, function_error=None, raise_error=None, payload_read_error=None
    ):
        self._payload = payload if payload is not None else {}
        self._function_error = function_error
        self._raise_error = raise_error
        self._payload_read_error = payload_read_error
        self.calls = []

    def invoke(self, **kwargs):
        self.calls.append(kwargs)
        if self._raise_error is not None:
            raise self._raise_error
        if self._payload_read_error is not None:
            return {"Payload": _RaisingPayload(self._payload_read_error)}
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
@pytest.mark.parametrize(
    "payload_read_error",
    [
        ReadTimeoutError(endpoint_url="https://lambda.example.com"),
        # Both raised by StreamingBody.read() after invoke() already returned; a
        # network fault partway through reading the response is transient like a
        # read timeout, not a reason to fail the image permanently.
        ResponseStreamingError(error=ConnectionResetError("connection reset")),
        IncompleteReadError(actual_bytes=10, expected_bytes=20),
        # botocore's conversion of a mid-flight connection reset (urllib3
        # ProtocolError); an HTTPClientError, not in the leaf tuple this guards.
        ConnectionClosedError(endpoint_url="https://lambda.example.com"),
    ],
)
def test_invoke_wraps_payload_read_timeout_as_retryable(monkeypatch, payload_read_error):
    """response["Payload"].read() can raise the identical exception invoke() raises
    two lines earlier; both must classify the same way instead of the read() one
    escaping unconverted with no .retryable attribute."""
    fake = _FakeClient(payload_read_error=payload_read_error)
    monkeypatch.setattr(inference, "get_lambda_client", lambda *a, **k: fake)

    with pytest.raises(InferenceError) as exc:
        invoke_pyspacer({"classifier_type": "pyspacer"})

    assert exc.value.retryable is True


@override_settings(INFERENCE_LAMBDA_PYSPACER="dev-mermaid-inference-pyspacer")
@pytest.mark.parametrize(
    "code,expected_retryable",
    [
        ("TooManyRequestsException", True),
        ("AccessDeniedException", False),
    ],
)
def test_invoke_classifies_client_error_retryability_by_code(monkeypatch, code, expected_retryable):
    """Only the transient/throttle codes let SQS redeliver; anything else (e.g. a
    permissions error) must fail the image once rather than loop to the DLQ."""
    error = ClientError({"Error": {"Code": code, "Message": "x"}}, "Invoke")
    fake = _FakeClient(raise_error=error)
    monkeypatch.setattr(inference, "get_lambda_client", lambda *a, **k: fake)

    with pytest.raises(InferenceError) as exc:
        invoke_pyspacer({"classifier_type": "pyspacer"})

    assert exc.value.retryable is expected_retryable


@override_settings(INFERENCE_LAMBDA_PYSPACER="dev-mermaid-inference-pyspacer")
@pytest.mark.parametrize(
    "function_error,error_message,expected_retryable",
    [
        ("Unhandled", "2026-09-15T00:00:00Z abc Task timed out after 600.10 seconds", True),
        ("Unhandled", "RequestId: abc Error: Runtime exited with error: signal: killed", True),
        # A deploy-broken image exiting at INIT with a plain status code is permanent
        # until rolled back, unlike the kill-signal case above; both share the
        # "Runtime exited" prefix, so the marker must not match on that alone.
        ("Unhandled", "RequestId: abc Error: Runtime exited with error: exit status 1", False),
        ("Unhandled", "ZeroDivisionError: division by zero", False),
        ("Handled", "Task timed out after 600.10 seconds", False),
    ],
)
def test_invoke_classifies_function_error_retryability(
    monkeypatch, function_error, error_message, expected_retryable
):
    """A synchronous invoke reports a Lambda timeout and a cold-start crash the same
    way as the function's own raised exception (FunctionError with a 200 status);
    only the decoded detail tells a genuine transient from a permanent one."""
    fake = _FakeClient(
        payload={"errorMessage": error_message, "errorType": "Sandbox.Timeout"},
        function_error=function_error,
    )
    monkeypatch.setattr(inference, "get_lambda_client", lambda *a, **k: fake)

    with pytest.raises(InferenceError) as exc:
        invoke_pyspacer({"classifier_type": "pyspacer"})

    assert exc.value.retryable is expected_retryable


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
    # Hand-derived from the 1500s visibility timeout budget (see
    # INFERENCE_JOB_VISIBILITY_TIMEOUT): 1 retry configured, so 2 total invokes.
    assert client.meta.config.retries["total_max_attempts"] == 2

    calls = []

    def fake_send(request):
        calls.append(request)
        raise ReadTimeoutError(endpoint_url=request.url)

    monkeypatch.setattr(client._endpoint.http_session, "send", fake_send)

    with pytest.raises(InferenceError):
        invoke_pyspacer({"classifier_type": "pyspacer"})

    assert len(calls) == 2
