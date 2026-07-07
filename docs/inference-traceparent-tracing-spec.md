# Spec: make the inference `traceparent` real (derive from the active span + log it)

- **Status:** proposed (follow-up to mermaid-classifier #54, which reserved the field)
- **Repos:** `mermaid-api` (derive + log), `mermaid-inference` (log in the function)
- **Contract:** no change — `PyspacerRequest`/`PyspacerResponse`/`ErrorEnvelope` already carry `traceparent`.

## Context

The classifier Lambda lane already threads a W3C `traceparent` through the synchronous
`lambda:Invoke` envelope: the API worker puts one in the request, and the function
mirrors it back into the response/error envelope. A synchronous Invoke carries no HTTP
headers, so the id rides in the JSON body — that's why the field exists on the contract.

Today the field is **inert plumbing**:

- `classify_via_lambda` (`src/api/utils/inference.py`) mints a **random** id via
  `new_traceparent()` — it is *not* derived from the worker's active OpenTelemetry/X-Ray
  span, so it is not the API's real trace id.
- Nothing **consumes** it: the function only echoes it; the API ignores `response.traceparent`;
  neither side logs it.

The API runs under ADOT (OpenTelemetry → X-Ray: `OTEL_PROPAGATORS=xray`, auto-instrumentation
incl. SQS) and the inference Lambda has X-Ray active tracing — but they are currently two
unrelated traces. This spec makes the `traceparent` carry the API's real trace id and logs
it on both ends, so a classification can be correlated across the invoke boundary.

## Goals

1. **Derive** the request `traceparent` from the worker's active OpenTelemetry span
   (its 128-bit trace id + current span id + sampled flag) instead of minting a random one.
2. **Log** the `trace_id` on both ends — the API worker (at invoke, and on failure) and the
   Lambda handler (on success and both error paths) — so a worker log line and the Lambda's
   CloudWatch logs are joinable by `trace_id`.

## Non-goals

- Making the Lambda's X-Ray **segment a child** of the API trace (full span-context adoption
  / propagation into the X-Ray daemon). Log-correlation is the deliverable here; deeper
  segment stitching is a later step.
- Fixing SQS trace-context propagation (whether the worker's span is itself linked to the
  originating HTTP upload). See "Dependency / caveat" below.
- Any contract change (the field already exists) or any change to classification behavior.

## Design

### mermaid-api

**Derive (`src/api/utils/inference.py`).** Replace the `new_traceparent()` call in
`classify_via_lambda` with a helper that reads the current span context:

```python
from opentelemetry import trace as otel_trace
from mermaid_inference_contract import Traceparent, format_traceparent, new_traceparent

def _current_traceparent() -> str:
    """W3C traceparent for the active OTEL span, or a fresh one if there is no valid span.

    OTEL span-context ids are already 128-bit trace / 64-bit span, i.e. W3C-shaped, so no
    X-Ray-format conversion is needed here; ADOT handles the X-Ray mapping at export.
    """
    ctx = otel_trace.get_current_span().get_span_context()
    if ctx.is_valid:
        return format_traceparent(
            Traceparent(
                trace_id=format(ctx.trace_id, "032x"),
                parent_id=format(ctx.span_id, "016x"),
                flags="01" if ctx.trace_flags.sampled else "00",
            )
        )
    return format_traceparent(new_traceparent())
```

`classify_via_lambda` calls `_current_traceparent()` instead of
`format_traceparent(new_traceparent())`. `build_pyspacer_request` is unchanged (still
receives the traceparent string).

**Guaranteed span (recommended, small).** The classify job runs in the image worker, not an
HTTP request, so an active span depends on auto-instrumentation. To make derivation reliable
and to give the invoke its own span, wrap the Lambda call in an explicit span in
`classify_via_lambda`:

```python
tracer = otel_trace.get_tracer("api.inference")
with tracer.start_as_current_span("pyspacer.classify_via_lambda"):
    traceparent = _current_traceparent()
    payload = invoke_pyspacer(build_pyspacer_request(image, points, traceparent))
    ...
```

This ensures `_current_traceparent()` sees a valid span (child of whatever the SQS/worker
auto-instrumentation provides, else a new root) rather than falling back to a random id.

**Log (`src/api/utils/inference.py`).** Add a module `logger = logging.getLogger(__name__)`
and log the id at the invoke boundary and on the failure paths, e.g.:

```python
logger.info("pyspacer inference invoke", extra={"traceparent": traceparent})
```

and include the traceparent in the `InferenceError` paths (error-envelope, drift, contract
mismatch) so a failed classification is traceable. Keep messages structured (the `extra`
dict) so `opentelemetry-instrumentation-logging` can attach trace context.

### mermaid-inference (function)

**Log (`packages/pyspacer-function/src/pyspacer_function/handler.py`).** Log the received
`traceparent` at the start of `handler()` and on each return, reusing the existing
`logger`. Extend the existing `[classify.processing_error]` marker line to include the
`trace_id` so a processing failure is joinable to the API worker's log:

```python
logger.info("pyspacer classify request", extra={"traceparent": _event_traceparent(event)})
...
logger.exception("[classify.processing_error] classify failed traceparent=%s", req.traceparent)
```

No behavior change; the handler already reads/echoes `traceparent`.

## Dependency / caveat

For the derived trace id to link back to the **originating upload** (HTTP request → SQS →
worker → classify), the worker's span must itself descend from the upload's trace — i.e. SQS
context propagation must inject the trace context on enqueue and extract it on consume.
That is provided by SQS auto-instrumentation if enabled end-to-end; if it is not, the derived
id still gives a valid trace for the worker→Lambda hop and log-correlation, just not stitched
to the HTTP request. Verifying/fixing SQS propagation is out of scope for this spec.

## Testing

- **mermaid-api (`src/api/tests/test_inference_lane.py`):**
  - `_current_traceparent()` with a stubbed **valid** span context (patch
    `otel_trace.get_current_span`) returns a traceparent whose `trace_id`/`parent_id` match
    the span context (32/16 hex); with an **invalid/absent** span it falls back to a
    well-formed `new_traceparent()` value.
  - `classify_via_lambda` logs the traceparent at invoke (assert via `caplog`) and the
    request carries the derived id (extend the existing `test_build_pyspacer_request_shape`
    / lane tests).
- **mermaid-inference (`packages/pyspacer-function/tests/test_handler.py`):** the handler
  logs the received `trace_id` on the success path and on a processing-error path (assert
  via `caplog`); the `[classify.processing_error]` line includes the traceparent.

## Rollout / impact

Purely additive observability — no change to request/response shape (the field already
exists), no change to classification results, safe under the `use_lambda=False` default
(the code path only runs when an env is on the Lambda lane). Ship the mermaid-api change with
the lane; the mermaid-inference logging change is an independent small PR in that repo.
