from aws_cdk import (
    Duration,
    aws_cloudwatch as cw,
    aws_cloudwatch_actions as cw_actions,
    aws_sns as sns,
    aws_sns_subscriptions as sns_subs,
    aws_sqs as sqs,
)
from constructs import Construct

from iac.settings.settings import ProjectSettings


class JobQueue(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        config: ProjectSettings,
        queue_name: str,
        fifo: bool = False,
        email: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # DLQ
        dead_letter_queue = sqs.Queue(
            self,
            "DLQ",
            fifo=True if fifo else None,  # Known cloudformation issue, set to None for none-fifo
            queue_name=f"{queue_name}-dql.fifo" if fifo else f"{queue_name}-dql",
            visibility_timeout=Duration.seconds(config.api.sqs_message_visibility),
            retention_period=Duration.days(7),
        )

        # FIFO Queue
        self.queue = sqs.Queue(
            self,
            "Queue",
            fifo=True if fifo else None,  # Known cloudformation issue, set to None for none-fifo
            queue_name=f"{queue_name}.fifo" if fifo else f"{queue_name}",
            content_based_deduplication=None,
            visibility_timeout=Duration.seconds(config.api.sqs_message_visibility),
            dead_letter_queue=sqs.DeadLetterQueue(max_receive_count=4, queue=dead_letter_queue),
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
