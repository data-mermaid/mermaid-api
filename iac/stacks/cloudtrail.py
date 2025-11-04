

from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_cloudtrail as cloudtrail
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk import aws_iam as iam
from aws_cdk import aws_logs as logs
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_sns as sns
from aws_cdk import aws_sns_subscriptions as subs
from constructs import Construct


class CloudTrailStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        **kwargs,
    ):
        super().__init__(scope, id, **kwargs)

        trail_bucket = s3.Bucket(
            self,
            "CloudTrailBucket",
            versioned=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            removal_policy=RemovalPolicy.RETAIN,
            auto_delete_objects=False,
            lifecycle_rules=[
                s3.LifecycleRule(
                    enabled=True,
                    expiration=Duration.days(365 * 3),
                    id="Expire old CloudTrail logs after 3 years",
                )
            ],
            enforce_ssl=True,
        )
        provider = self.node.try_find_child("CustomS3AutoDeleteObjectsCustomResourceProvider")
        if provider:
            handler = provider.node.try_find_child("Handler")
            if handler and hasattr(handler, "role") and handler.role:
                handler.role.add_to_principal_policy(
                    iam.PolicyStatement(
                        actions=["s3:GetBucketTagging"],
                        resources=[trail_bucket.bucket_arn],
                    )
                )

        log_group = logs.LogGroup(
            self,
            "CloudTrailLogGroup",
            retention=logs.RetentionDays.ONE_YEAR,
            removal_policy=RemovalPolicy.RETAIN,
        )

        # SNS topic for CloudTrail log delivery notifications
        delivery_topic = sns.Topic(
            self,
            "CloudTrailDeliveryTopic",
            display_name="CloudTrail Log Delivery Notifications",
        )
        # Allow CloudTrail service to publish
        delivery_topic.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AllowCloudTrailPublish",
                effect=iam.Effect.ALLOW,
                principals=[iam.ServicePrincipal("cloudtrail.amazonaws.com")],
                actions=["sns:Publish"],
                resources=[delivery_topic.topic_arn],
            )
        )

        # Trail with SNS notification delivery enabled
        trail = cloudtrail.Trail(
            self,
            "CloudTrail",
            bucket=trail_bucket,
            cloud_watch_log_group=log_group,
            cloud_watch_logs_retention=logs.RetentionDays.THREE_YEARS,
            enable_file_validation=True,
            include_global_service_events=True,
            insight_types=[
                cloudtrail.InsightType.API_CALL_RATE,
                cloudtrail.InsightType.API_ERROR_RATE,
            ],
            is_multi_region_trail=True,
            management_events=cloudtrail.ReadWriteType.ALL,
            send_to_cloud_watch_logs=True,
            sns_topic=delivery_topic,
        )
        trail.log_all_lambda_data_events()
        trail.log_all_s3_data_events()

        CfnOutput(self, "CloudTrailBucketName", value=trail_bucket.bucket_name)
        CfnOutput(self, "CloudTrailDeliveryTopicArn", value=delivery_topic.topic_arn)

        delete_topic = sns.Topic(
            self, "CloudTrailDeleteTopic", display_name="CloudTrail Delete Events Topic"
        )
        delete_topic.add_subscription(subs.EmailSubscription("system@datamermaid.org"))

        CfnOutput(self, "DeleteTopicArn", value=delete_topic.topic_arn)

        rule = events.Rule(
            self,
            "CloudTrailDeleteEventsRule",
            enabled=True,
            event_pattern=events.EventPattern(
                detail_type=["AWS API Call via CloudTrail"],
                detail={
                    "eventName": [
                        {"prefix": "Delete"},
                        {"prefix": "Terminate"},
                        {"prefix": "Remove"},
                        {"prefix": "Destroy"},
                    ],
                },
            ),
        )

        rule.add_target(targets.SnsTopic(delete_topic))