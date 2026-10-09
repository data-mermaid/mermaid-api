# mermaid-api/iac/stacks/inference.py
from aws_cdk import (
    Duration,
    RemovalPolicy,
    Size,
    Stack,
    aws_cloudwatch as cw,
    aws_cloudwatch_actions as cw_actions,
    aws_ecr as ecr,
    aws_lambda as lambda_,
    aws_logs as logs,
    aws_s3 as s3,
    aws_sns as sns,
)
from constructs import Construct
from settings.settings import ProjectSettings, alerts_topic_name, pyspacer_function_name


class InferenceStack(Stack):
    """The pyspacer inference compute lane (mermaid-classifier issue #53).

    A non-VPC container Lambda that runs EfficientNet extraction + the portable
    TorchScript classifier head. The function serves the single model version
    baked into its image at build time (CLASSIFIER_VERSION), resolving
    `classifier/<version>/` from the config bucket at runtime. The image tag
    (config.inference.image_tag) is the model-build tag `vN-K` (model version +
    serving build) pinned here in IaC — git history is the deploy log.

    Alarms publish to the shared per-env alerts topic owned by ApiStack's
    MonitoringAlerts construct; that construct's single Chatbot config delivers
    everything on the topic to Slack, so this stack creates no delivery infra.
    The topic is resolved from its deterministic name (alerts_topic_name), not
    from an ApiStack construct — see the alarms section below.
    """

    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        config: ProjectSettings,
        inference_repo: ecr.IRepository,
        config_bucket: s3.IBucket,
        image_buckets: list[tuple[s3.IBucket, str]],
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        inf = config.inference

        # Explicit log group — otherwise Lambda auto-creates /aws/lambda/<fn>
        # with "Never expire" retention and an orphaned-on-stack-delete group.
        log_group = logs.LogGroup(
            self,
            "PyspacerInferenceFunctionLogGroup",
            log_group_name=f"/aws/lambda/{pyspacer_function_name(config.env_id)}",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY,
        )

        self.function = lambda_.DockerImageFunction(
            self,
            "PyspacerInferenceFunction",
            function_name=pyspacer_function_name(config.env_id),
            code=lambda_.DockerImageCode.from_ecr(
                repository=inference_repo,
                tag_or_digest=inf.image_tag,
            ),
            log_group=log_group,
            architecture=lambda_.Architecture.ARM_64,
            memory_size=inf.memory_mb,
            timeout=Duration.minutes(inf.timeout_minutes),
            ephemeral_storage_size=Size.gibibytes(inf.ephemeral_storage_gb),
            reserved_concurrent_executions=inf.reserved_concurrency,
            tracing=lambda_.Tracing.ACTIVE,
            environment={
                "CONFIG_BUCKET": inf.config_bucket,
                "INFERENCE_NUM_THREADS": str(inf.num_threads),
            },
        )

        # Read-only on classifier/*: the legacy lane unpickles classifier.pkl through
        # pyspacer's ClassifierUnpickler, which delegates to stock pickle.Unpickler with
        # no allowlist, so write access here is code execution as this role on a cold start.
        config_bucket.grant_read(self.function, "classifier/*")

        # (bucket, key prefix) per env: the function reads source images and writes
        # extracted feature vectors back under the same prefix, in every image
        # bucket including the foreign coral-reef-training bucket, whose policy
        # grants this function's exact name a matching put statement.
        for bucket, prefix in image_buckets:
            bucket.grant_read(self.function, f"{prefix}*")
            bucket.grant_put(self.function, f"{prefix}*")

        # ── Alarms ──────────────────────────────────────────────────
        # Imported by ARN from the name both stacks compute. ApiStack's topic construct
        # would make CDK deploy ApiStack first, and the API must not expect a classifier
        # version before this stack's Lambda serves it. No topic/Chatbot created here.
        alerts_topic = sns.Topic.from_topic_arn(
            self,
            "AlertsTopic",
            f"arn:aws:sns:{self.region}:{self.account}:{alerts_topic_name(config.env_id)}",
        )
        sns_action = cw_actions.SnsAction(alerts_topic)

        for construct_id, metric, alarm_name, description in (
            (
                "ErrorsAlarm",
                self.function.metric_errors(statistic="Sum", period=Duration.minutes(5)),
                f"mermaid-{config.env_id}-inference-errors",
                "Inference Lambda invocation errors (OOM / timeout / INIT crash / "
                "unhandled fault) — 1 or more in a 5-minute window",
            ),
            (
                "ThrottlesAlarm",
                self.function.metric_throttles(statistic="Sum", period=Duration.minutes(5)),
                f"mermaid-{config.env_id}-inference-throttles",
                "Inference Lambda invocations throttled (reserved concurrency "
                "exhausted) — 1 or more in a 5-minute window",
            ),
        ):
            alarm = cw.Alarm(
                self,
                construct_id,
                alarm_name=alarm_name,
                alarm_description=description,
                metric=metric,
                threshold=1,
                evaluation_periods=1,
                comparison_operator=cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
                treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
            )
            alarm.add_alarm_action(sns_action)
            alarm.add_ok_action(sns_action)

        # Processing-error visibility (the Errors metric can't see these).
        # The handler returns model/infra failures as PROCESSING_ERROR envelopes
        # rather than raising, so the Lambda Errors metric stays 0. It logs a
        # stable "[classify.processing_error]" marker (NOT on the validation path);
        # this metric filter turns that marker into a count, alarmed on a
        # threshold so a systemic failure (bad artifact, unresolvable version)
        # pages, while a single bad image does not. Mirrors the Auth0/Sentry
        # log-metric-filter pattern in stacks/constructs/alerts.py.
        processing_error_metric = logs.MetricFilter(
            self,
            "ProcessingErrorMetricFilter",
            log_group=log_group,
            filter_pattern=logs.FilterPattern.literal('"[classify.processing_error]"'),
            metric_namespace=f"MERMAID/{config.env_id}/Inference",
            metric_name="ProcessingErrors",
            metric_value="1",
            default_value=0,
        )
        processing_errors_alarm = cw.Alarm(
            self,
            "ProcessingErrorsAlarm",
            alarm_name=f"mermaid-{config.env_id}-inference-processing-errors",
            alarm_description=(
                "Inference Lambda returned PROCESSING_ERROR envelopes (model/infra "
                "failures invisible to the Errors metric) — 5 or more in a 5-minute "
                "window, e.g. a bad model artifact or unresolvable classifier_version"
            ),
            metric=processing_error_metric.metric(statistic="Sum", period=Duration.minutes(5)),
            threshold=5,
            evaluation_periods=1,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
        )
        processing_errors_alarm.add_alarm_action(sns_action)
        processing_errors_alarm.add_ok_action(sns_action)

        # Feature-store write failures: classification succeeds but the vector can't be
        # persisted, so it returns success with feature_vector_output: null and nothing
        # retries — the vector is lost. The marker is emitted by pyspacer_function.classify
        # in data-mermaid/mermaid-inference; the two must stay in sync.
        feature_store_error_metric = logs.MetricFilter(
            self,
            "FeatureStoreErrorMetricFilter",
            log_group=log_group,
            filter_pattern=logs.FilterPattern.literal('"[classify.feature_store_error]"'),
            metric_namespace=f"MERMAID/{config.env_id}/Inference",
            metric_name="FeatureStoreErrors",
            metric_value="1",
            default_value=0,
        )
        feature_store_errors_alarm = cw.Alarm(
            self,
            "FeatureStoreErrorsAlarm",
            alarm_name=f"mermaid-{config.env_id}-inference-feature-store-errors",
            alarm_description=(
                "Inference Lambda classified successfully but could not persist the "
                "feature vector (invisible to the Errors metric and to "
                "ProcessingErrors; the vector is lost permanently) — 5 or more in a "
                "5-minute window, e.g. an AccessDenied on the feature-vector bucket "
                "or a bucket-policy regression"
            ),
            metric=feature_store_error_metric.metric(statistic="Sum", period=Duration.minutes(5)),
            threshold=5,
            evaluation_periods=1,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
        )
        feature_store_errors_alarm.add_alarm_action(sns_action)
        feature_store_errors_alarm.add_ok_action(sns_action)
