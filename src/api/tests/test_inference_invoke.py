import io
import json

import pytest
from django.test import override_settings

from api.utils import inference
from api.utils.inference import InferenceError, invoke_pyspacer


class _FakeClient:
    def __init__(self, *, payload=None, function_error=None):
        self._payload = payload if payload is not None else {}
        self._function_error = function_error
        self.calls = []

    def invoke(self, **kwargs):
        self.calls.append(kwargs)
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
