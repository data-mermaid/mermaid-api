# mermaid-api/iac/stacks/inference.py
from aws_cdk import (
    Duration,
    Size,
    Stack,
    aws_chatbot as chatbot,
    aws_cloudwatch as cw,
    aws_cloudwatch_actions as cw_actions,
    aws_ecr as ecr,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_s3 as s3,
    aws_sns as sns,
)
from constructs import Construct
from settings.settings import ProjectSettings


class InferenceStack(Stack):
    """The pyspacer inference compute lane (issue #53).

    A non-VPC container Lambda that runs EfficientNet extraction + the portable
    TorchScript classifier head. The image is model-agnostic: it resolves model
    files from the request's classifier_version against the config bucket at
    runtime. The image tag (config.inference.image_version) is a mermaid-inference
    semver pinned here in IaC — git history is the deploy log.
    """

    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        config: ProjectSettings,
        inference_repo: ecr.IRepository,
        config_bucket: s3.IBucket,
        image_bucket: s3.IBucket,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        inf = config.inference

        self.function = lambda_.DockerImageFunction(
            self,
            "PyspacerInferenceFunction",
            function_name=f"{config.env_id}-mermaid-inference-pyspacer",
            code=lambda_.DockerImageCode.from_ecr(
                repository=inference_repo,
                tag_or_digest=inf.image_version,
            ),
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

        # Same-account reads (dev). No assume-role, no long-lived keys.
        config_bucket.grant_read(self.function, "classifier/*")
        image_bucket.grant_read(self.function)

        # ── Alarms (issue #53 AC) ───────────────────────────────────
        alerts_topic = sns.Topic(self, "InferenceAlertsTopic")
        sns_action = cw_actions.SnsAction(alerts_topic)

        for name, metric in (
            ("ErrorsAlarm", self.function.metric_errors(statistic="Sum", period=Duration.minutes(5))),
            ("ThrottlesAlarm", self.function.metric_throttles(statistic="Sum", period=Duration.minutes(5))),
        ):
            alarm = cw.Alarm(
                self,
                name,
                metric=metric,
                threshold=1,
                evaluation_periods=1,
                comparison_operator=cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
                treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
            )
            alarm.add_alarm_action(sns_action)
            alarm.add_ok_action(sns_action)

        # Optional Slack delivery via AWS Chatbot (mirrors stacks/constructs/alerts.py).
        slack_workspace_id = config.api.slack_workspace_id or None
        slack_channel_id = config.api.slack_channel_id or None
        if slack_workspace_id and slack_channel_id:
            slack_role = iam.Role(
                self,
                "InferenceSlackRole",
                assumed_by=iam.ServicePrincipal("chatbot.amazonaws.com"),
                managed_policies=[
                    iam.ManagedPolicy.from_aws_managed_policy_name("AmazonQDeveloperAccess"),
                ],
            )
            chatbot.SlackChannelConfiguration(
                self,
                "InferenceSlackChannel",
                slack_channel_configuration_name=f"mermaid-{config.env_id}-inference-alerts",
                slack_workspace_id=slack_workspace_id,
                slack_channel_id=slack_channel_id,
                notification_topics=[alerts_topic],
                role=slack_role,
                guardrail_policies=[
                    iam.ManagedPolicy.from_aws_managed_policy_name("AmazonQDeveloperAccess"),
                ],
            )
