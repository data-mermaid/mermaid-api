from aws_cdk import (
    Duration,
    aws_chatbot as chatbot,
    aws_cloudwatch as cw,
    aws_cloudwatch_actions as cw_actions,
    aws_ecs as ecs,
    aws_elasticloadbalancingv2 as elb,
    aws_iam as iam,
    aws_logs as logs,
    aws_rds as rds,
    aws_sns as sns,
    aws_sqs as sqs,
)
from constructs import Construct


class MonitoringAlerts(Construct):
    """
    CloudWatch alarms for key health signals, wired to a shared SNS topic.

    If slack_workspace_id and slack_channel_id are provided, an AWS Chatbot
    Slack channel configuration is created that subscribes to the topic.
    The Slack workspace must be connected to AWS Chatbot in the console first
    (Settings → Integrations → Slack) before CDK can reference it by workspace ID.
    """

    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        env_id: str,
        load_balancer: elb.IApplicationLoadBalancer,
        api_service: ecs.Ec2Service,
        database: rds.DatabaseInstance,
        general_dlq: sqs.IQueue,
        image_dlq: sqs.IQueue,
        api_log_group: logs.ILogGroup,
        sagemaker_domain_name: str | None = None,
        slack_workspace_id: str | None = None,
        slack_channel_id: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        self.topic = sns.Topic(
            self,
            "AlertsTopic",
            display_name=f"mermaid-{env_id}-alerts",
            topic_name=f"mermaid-{env_id}-alerts",
        )
        sns_action = cw_actions.SnsAction(self.topic)

        alarms: list[cw.Alarm] = []

        # ── ALB ──────────────────────────────────────────────────────

        alarms.append(
            cw.Alarm(
                self,
                "Alb5xxAlarm",
                alarm_name=f"mermaid-{env_id}-alb-5xx-errors",
                alarm_description="ALB Target 5xx errors exceeded 10 in a 5-minute window",
                metric=load_balancer.metrics.http_code_target(
                    code=elb.HttpCodeTarget.TARGET_5XX_COUNT,
                    statistic="Sum",
                    period=Duration.minutes(5),
                ),
                threshold=10,
                evaluation_periods=1,
                comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
                treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
            )
        )

        alarms.append(
            cw.Alarm(
                self,
                "AlbLatencyAlarm",
                alarm_name=f"mermaid-{env_id}-alb-p99-latency",
                alarm_description="ALB p99 response latency exceeded 5 seconds",
                metric=load_balancer.metrics.target_response_time(
                    statistic="p99",
                    period=Duration.minutes(5),
                ),
                threshold=5,
                evaluation_periods=2,
                comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
                treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
            )
        )

        # ── RDS ──────────────────────────────────────────────────────

        alarms.append(
            cw.Alarm(
                self,
                "RdsCpuAlarm",
                alarm_name=f"mermaid-{env_id}-rds-cpu",
                alarm_description="RDS CPU utilization exceeded 80% for 10 minutes",
                metric=database.metric_cpu_utilization(period=Duration.minutes(5)),
                threshold=80,
                evaluation_periods=2,
                comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
                treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
            )
        )

        # db.t3.medium has ~170 max_connections by default; 100 is a reasonable warning threshold
        alarms.append(
            cw.Alarm(
                self,
                "RdsConnectionsAlarm",
                alarm_name=f"mermaid-{env_id}-rds-connections",
                alarm_description="RDS database connections exceeded 100 for 10 minutes",
                metric=database.metric_database_connections(period=Duration.minutes(5)),
                threshold=100,
                evaluation_periods=2,
                comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
                treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
            )
        )

        # ── ECS API ──────────────────────────────────────────────────

        alarms.append(
            cw.Alarm(
                self,
                "ApiCpuAlarm",
                alarm_name=f"mermaid-{env_id}-api-cpu",
                alarm_description="API ECS service CPU utilization exceeded 85% for 10 minutes",
                metric=api_service.metric_cpu_utilization(period=Duration.minutes(5)),
                threshold=85,
                evaluation_periods=2,
                comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
                treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
            )
        )

        alarms.append(
            cw.Alarm(
                self,
                "EcsTaskStoppedAlarm",
                alarm_name=f"mermaid-{env_id}-ecs-no-running-tasks",
                alarm_description=(
                    "API ECS service has 0 running tasks for 2 consecutive minutes — "
                    "deployment failure or crash loop"
                ),
                metric=api_service.metric(
                    "RunningTaskCount",
                    statistic="Minimum",
                    period=Duration.minutes(1),
                ),
                threshold=1,
                evaluation_periods=2,
                comparison_operator=cw.ComparisonOperator.LESS_THAN_THRESHOLD,
                treat_missing_data=cw.TreatMissingData.BREACHING,
            )
        )

        alarms.append(
            cw.Alarm(
                self,
                "ApiMemoryAlarm",
                alarm_name=f"mermaid-{env_id}-api-memory",
                alarm_description="API ECS service memory utilization exceeded 85% for 10 minutes",
                metric=cw.Metric(
                    namespace="ECS/ContainerInsights",
                    metric_name="MemoryUtilization",
                    dimensions_map={
                        "ClusterName": api_service.cluster.cluster_name,
                        "ServiceName": api_service.service_name,
                    },
                    statistic="Average",
                    period=Duration.minutes(5),
                ),
                threshold=85,
                evaluation_periods=2,
                comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
                treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
            )
        )

        # ── SQS DLQs ─────────────────────────────────────────────────
        # queue.py also has per-queue DLQ alarms wired to email topics; these
        # are separate alarms on the same metric, wired to this shared Slack topic.

        alarms.append(
            cw.Alarm(
                self,
                "GeneralDlqAlarm",
                alarm_name=f"mermaid-{env_id}-general-dlq",
                alarm_description="Messages in general DLQ — worker task failures",
                metric=general_dlq.metric_approximate_number_of_messages_visible(
                    statistic="Maximum",
                    period=Duration.minutes(5),
                ),
                threshold=1,
                evaluation_periods=1,
                comparison_operator=cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
                treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
            )
        )

        alarms.append(
            cw.Alarm(
                self,
                "ImageDlqAlarm",
                alarm_name=f"mermaid-{env_id}-image-dlq",
                alarm_description="Messages in image-processing DLQ — classification task failures",
                metric=image_dlq.metric_approximate_number_of_messages_visible(
                    statistic="Maximum",
                    period=Duration.minutes(5),
                ),
                threshold=1,
                evaluation_periods=1,
                comparison_operator=cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
                treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
            )
        )

        # ── SageMaker cost alert ──────────────────────────────────────
        # Fires when Studio apps are left running to prevent unexpected spend.

        if sagemaker_domain_name:
            alarms.append(
                cw.Alarm(
                    self,
                    "SageMakerRunningAppsAlarm",
                    alarm_name=f"mermaid-{env_id}-sagemaker-running-apps",
                    alarm_description=(
                        "SageMaker Studio apps are running — check for idle sessions to avoid cost"
                    ),
                    metric=cw.Metric(
                        namespace="/aws/sagemaker/Domains",
                        metric_name="RunningAppCount",
                        statistic="Maximum",
                        dimensions_map={"DomainName": sagemaker_domain_name},
                        period=Duration.hours(1),
                    ),
                    threshold=0,
                    evaluation_periods=2,
                    comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
                    treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
                )
            )

        # ── Auth0 (app-side instrumentation) ─────────────────────────
        # Metric filters match structured markers logged by auth_backends.py
        # and auth0utils.py. The entire log event is text, so we use keyword
        # matching rather than JSON pattern syntax.

        failed_auth_metric = logs.MetricFilter(
            self,
            "FailedAuthMetricFilter",
            log_group=api_log_group,
            filter_pattern=logs.FilterPattern.literal('"[auth0.failed_auth]"'),
            metric_namespace=f"MERMAID/{env_id}/Auth0",
            metric_name="FailedAuthentications",
            metric_value="1",
            default_value=0,
        )
        alarms.append(
            cw.Alarm(
                self,
                "FailedAuthAlarm",
                alarm_name=f"mermaid-{env_id}-auth0-failed-auth",
                alarm_description=(
                    "Auth0 authentication failures exceeded 20 in 5 minutes — "
                    "possible credential stuffing or token replay attack"
                ),
                metric=failed_auth_metric.metric(
                    statistic="Sum",
                    period=Duration.minutes(5),
                ),
                threshold=20,
                evaluation_periods=1,
                comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
                treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
            )
        )

        auth0_unavailable_metric = logs.MetricFilter(
            self,
            "Auth0UnavailableMetricFilter",
            log_group=api_log_group,
            filter_pattern=logs.FilterPattern.literal('"[auth0.service_unavailable]"'),
            metric_namespace=f"MERMAID/{env_id}/Auth0",
            metric_name="ServiceUnavailable",
            metric_value="1",
            default_value=0,
        )
        alarms.append(
            cw.Alarm(
                self,
                "Auth0UnavailableAlarm",
                alarm_name=f"mermaid-{env_id}-auth0-service-unavailable",
                alarm_description=(
                    "Auth0 Management API is returning errors or timing out — "
                    "user profile lookups are failing"
                ),
                metric=auth0_unavailable_metric.metric(
                    statistic="Sum",
                    period=Duration.minutes(5),
                ),
                threshold=3,
                evaluation_periods=1,
                comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
                treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
            )
        )

        rate_limit_metric = logs.MetricFilter(
            self,
            "Auth0RateLimitMetricFilter",
            log_group=api_log_group,
            filter_pattern=logs.FilterPattern.literal('"[auth0.rate_limit]"'),
            metric_namespace=f"MERMAID/{env_id}/Auth0",
            metric_name="RateLimitHit",
            metric_value="1",
            default_value=0,
        )
        alarms.append(
            cw.Alarm(
                self,
                "Auth0RateLimitAlarm",
                alarm_name=f"mermaid-{env_id}-auth0-rate-limit",
                alarm_description=(
                    "Auth0 Management API rate limit hit — "
                    "too many user info lookups; consider caching tokens"
                ),
                metric=rate_limit_metric.metric(
                    statistic="Sum",
                    period=Duration.minutes(5),
                ),
                threshold=1,
                evaluation_periods=1,
                comparison_operator=cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
                treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
            )
        )

        # ── Sentry (before_send hook → CloudWatch → SNS → Slack) ────────
        # _sentry_before_send in settings.py emits [sentry.error_captured] on
        # every event forwarded to Sentry, routing error counts through the
        # existing CloudWatch → SNS → Chatbot pipeline at no extra cost.

        sentry_metric = logs.MetricFilter(
            self,
            "SentryErrorMetricFilter",
            log_group=api_log_group,
            filter_pattern=logs.FilterPattern.literal('"[sentry.error_captured]"'),
            metric_namespace=f"MERMAID/{env_id}/Sentry",
            metric_name="ErrorsCaptured",
            metric_value="1",
            default_value=0,
        )
        alarms.append(
            cw.Alarm(
                self,
                "SentryErrorAlarm",
                alarm_name=f"mermaid-{env_id}-sentry-errors",
                alarm_description=(
                    "Sentry captured more than 10 errors in 5 minutes — "
                    "check Sentry dashboard for details"
                ),
                metric=sentry_metric.metric(
                    statistic="Sum",
                    period=Duration.minutes(5),
                ),
                threshold=10,
                evaluation_periods=1,
                comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
                treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
            )
        )

        # Wire all alarms to the shared topic (alarm and recovery notifications)
        for alarm in alarms:
            alarm.add_alarm_action(sns_action)
            alarm.add_ok_action(sns_action)

        # ── AWS Chatbot Slack integration ─────────────────────────────
        # Requires the Slack workspace to be connected in the AWS Console first:
        # AWS Chatbot → Configured clients → Slack → Add client → authorize workspace
        # The workspace ID is then visible in the Chatbot console.

        if slack_workspace_id and slack_channel_id:
            # Scoped read-only policy: observability services only, no broad account enumeration.
            # Used on both the channel role and as the guardrail so effective permissions
            # are the intersection — scoped reads + Q Developer, nothing else.
            _observability_actions = [
                "cloudwatch:Describe*",
                "cloudwatch:Get*",
                "cloudwatch:List*",
                "logs:Describe*",
                "logs:Get*",
                "logs:List*",
                "logs:FilterLogEvents",
                "logs:StartQuery",
                "logs:StopQuery",
                "ecs:Describe*",
                "ecs:List*",
                "rds:Describe*",
                "rds:List*",
                "cloudformation:Describe*",
                "cloudformation:List*",
                "cloudformation:Get*",
                "sns:Get*",
                "sns:List*",
                "sqs:Get*",
                "sqs:List*",
            ]
            observability_policy = iam.ManagedPolicy(
                self,
                "SlackObservabilityPolicy",
                managed_policy_name=f"mermaid-{env_id}-slack-observability",
                statements=[
                    iam.PolicyStatement(
                        actions=_observability_actions,
                        resources=["*"],
                    )
                ],
            )
            slack_channel_role = iam.Role(
                self,
                "SlackChannelConfigurationRole",
                assumed_by=iam.ServicePrincipal("chatbot.amazonaws.com"),
                managed_policies=[
                    iam.ManagedPolicy.from_aws_managed_policy_name("AmazonQDeveloperAccess"),
                    observability_policy,
                ],
            )
            chatbot.SlackChannelConfiguration(
                self,
                "SlackChannel",
                slack_channel_configuration_name=f"mermaid-{env_id}-alerts",
                slack_workspace_id=slack_workspace_id,
                slack_channel_id=slack_channel_id,
                notification_topics=[self.topic],
                role=slack_channel_role,
                # Guardrail = hard ceiling on effective permissions
                guardrail_policies=[
                    iam.ManagedPolicy.from_aws_managed_policy_name("AmazonQDeveloperAccess"),
                    observability_policy,
                ],
            )
