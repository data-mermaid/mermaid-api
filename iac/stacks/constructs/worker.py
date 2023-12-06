from constructs import Construct
from aws_cdk import (
    Duration,
    aws_sqs as sqs,
    aws_cloudwatch as cw,
    aws_cloudwatch_actions as cw_actions,
    aws_sns as sns,
    aws_sns_subscriptions as sns_subs,
    aws_ecs_patterns as ecs_patterns,
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_applicationautoscaling as appscaling,
    aws_s3 as s3,
)

from iac.settings.settings import ProjectSettings

class QueueWorker(Construct):
    def __init__(
        self, 
        scope: Construct, 
        id: str, 
        config: ProjectSettings,
        cluster: ecs.Cluster,
        image_asset: ecs.ContainerImage,
        container_security_group: ec2.SecurityGroup,
        api_secrets: dict,
        environment: dict,
        public_bucket: s3.Bucket,
        queue_name: str,
        email: str = None,
        **kwargs,
    ) -> None:
        
        super().__init__(scope, id, **kwargs)

        # DLQ
        dead_letter_queue = sqs.Queue(
            self,
            "DLQ",
            fifo=True,
            queue_name=f"{queue_name}-dql.fifo",
            visibility_timeout=Duration.seconds(config.api.sqs_message_visibility),
            retention_period=Duration.days(7),
        )

        # FIFO Queue
        queue = sqs.Queue(
            self,
            "Queue",
            fifo=True,
            queue_name=f"{queue_name}.fifo",
            content_based_deduplication=False,
            visibility_timeout=Duration.seconds(config.api.sqs_message_visibility),
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=2, 
                queue=dead_letter_queue
            ),
        )

        # CloudWatch Alarm for DLQ
        dlq_alarm = cw.Alarm(
            self,
            "DLQAlarm",
            metric=dead_letter_queue.metric_approximate_number_of_messages_visible(
                statistic="Maximum",
            ),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cw.TreatMissingData.IGNORE,
        )

        # SNS Topic & Subscription
        topic = sns.Topic(self, "Topic")
        if email:   
            topic.add_subscription(sns_subs.EmailSubscription(email))

        # Add SNS Action to CloudWatch Alarms
        sns_action = cw_actions.SnsAction(topic=topic)

        dlq_alarm.add_alarm_action(sns_action)
        dlq_alarm.add_ok_action(sns_action)

        # Fargate Service for Worker Task
        fargate_service = ecs_patterns.QueueProcessingFargateService(
            self,
            "Service",
            cluster=cluster,
            queue=queue,
            image=ecs.ContainerImage.from_docker_image_asset(image_asset),
            cpu=config.api.sqs_cpu,
            memory_limit_mib=config.api.sqs_memory,
            security_groups=[container_security_group],
            secrets=api_secrets,
            environment=environment,
            command=["python", "manage.py", "simpleq_worker"],
            min_scaling_capacity=0,  # service should only run if ness
            max_scaling_capacity=1,  # only run one task at a time to process messages
            # this defines how the service shall autoscale based on the
            # SQS queue's ApproximateNumberOfMessagesVisible metric
            scaling_steps=[
                # when 0 messages, scale down
                appscaling.ScalingInterval(upper=0, change=-1),
                # when >=1 messages, scale up
                appscaling.ScalingInterval(lower=1, change=+1),
            ],
        )

        # allow worker access to public bucket
        public_bucket.grant_read_write(fargate_service.task_definition.task_role)

        # exports
        self.queue = queue