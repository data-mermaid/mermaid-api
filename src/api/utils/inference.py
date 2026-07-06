import json

import boto3
from django.conf import settings


class InferenceError(Exception):
    """Raised when the inference Lambda invocation fails or returns an error envelope."""


def get_lambda_client(aws_access_key_id=None, aws_secret_access_key=None):
    session = boto3.session.Session(
        aws_access_key_id=aws_access_key_id or settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=aws_secret_access_key or settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )
    return session.client("lambda")


def invoke_pyspacer(payload: dict) -> dict:
    """Invoke the pyspacer inference Lambda synchronously and return its parsed payload.

    Raises InferenceError if the function crashed (FunctionError present). A business
    failure is NOT a FunctionError — it comes back as a normal payload (ErrorEnvelope),
    handled by the caller.
    """
    client = get_lambda_client()
    response = client.invoke(
        FunctionName=settings.INFERENCE_LAMBDA_PYSPACER,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload).encode("utf-8"),
    )
    raw = response["Payload"].read()
    if response.get("FunctionError"):
        detail = raw.decode("utf-8", errors="replace")[:500]
        raise InferenceError(f"Lambda FunctionError ({response['FunctionError']}): {detail}")
    return json.loads(raw)
