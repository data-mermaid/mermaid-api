# Task and worker telemetry

The API uses `ObservableThreadWorker`, a Gunicorn gthread subclass that instruments
the supported thread-pool hook. ECS enables it with `MERMAID_WORKER_TELEMETRY=1`;
without that setting it uses the standard thread pool. Every ten seconds each worker
emits a `WorkerTelemetry` JSON event to the existing API log stream. CloudWatch EMF
publishes its numeric fields under `Mermaid/Workers`, with cluster, service, task,
and worker PID dimensions. Task identity comes from the ECS v4 metadata endpoint.

`BusyThreads` measures occupied connection-processing threads, including client I/O.
`ActiveRequests` measures active HTTP/1 request handlers. `QueuedConnections`
counts jobs waiting for a worker thread; `QueueWaitMaxMs` is the maximum completed
queue wait observed during the sampling interval. `CompletedConnections` counts
finished connection jobs during that interval, not unique HTTP requests. Gauges
are snapshots, so short bursts between samples may be missed. Metric failures do
not fail requests. Container Insights is configured for enhanced task metrics.

The current Django database configuration has no application connection pool.
No database-pool wait metric is emitted, and worker occupancy must not be presented
as database or CPU saturation. Correlate task CPU, queue wait, and existing traces.
Enhanced Container Insights and task/worker EMF dimensions add CloudWatch usage.


Run `pytest -q -c /dev/null -p no:django -p no:cacheprovider tests/observability` with pytest and Gunicorn 26 installed. Deploy the infrastructure and API before expecting these measurements.
