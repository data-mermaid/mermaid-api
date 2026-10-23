# Build provenance and task history

CI passes the full `GITHUB_SHA` into the shared runtime image's OCI revision label.
After successful CDK deployment it reads the CDK asset's ECR digest and appends a
`BuildProvenance` record to `/mermaid/ENV/deployments`. The record includes the full
Git SHA, source repository, image repository/digest, task-definition ARN, timestamp,
and CI run URL. Records use a distinct stream per build/run attempt and are never
updated by the publisher. CloudWatch retention is one year; stack removal retains
the log group. This is an operational provenance record, not a signed attestation.

A service-filtered EventBridge rule also archives ECS Task State Change events in
that group, retaining image digests and lifecycle timestamps after old ECS tasks
disappear. Dev and prod share a cluster but each rule selects its own API service.
Neither a task-state event nor a build mapping proves a task served a particular
request. Existing incidents remain unmapped if historical records are absent.

For manual builds, set `BUILD_GIT_SHA` to the full source commit before CDK synthesis.
An unset value produces an explicitly unknown image revision; the CI publisher
rejects missing, abbreviated, or inconsistent revisions rather than guessing.

Validation without the application database:

```sh
python -m pytest -q -c /dev/null -p no:django -p no:cacheprovider tests/observability
```

These tests require pytest and boto3. The CDK changes
and workflow must be deployed before new telemetry/provenance becomes available.
