from constructs import Construct
from aws_cdk import (
    Duration,
    aws_sqs as sqs,
    aws_cloudwatch as cw,
    aws_cloudwatch_actions as cw_actions,
    aws_sns as sns,
    aws_sns_subscriptions as sns_subs,
)

from iac.settings.settings import ProjectSettings

class MonitoredQueue(Construct):
    def __init__(
        self, 
        scope: Construct, 
        id: str, 
        config: ProjectSettings,
        email: str = None,
        **kwargs,
    ) -> None:
        
        super().__init__(scope, id, **kwargs)

        # DLQ
        dead_letter_queue = sqs.Queue(
            self,
            "DeadLetterQueue",
            queue_name=f"mermaid-{config.env_id}-deadletter",
            retention_period=Duration.days(7),
        )

        # FIFO Queue
        queue = sqs.Queue(
            self,
            "FifoQueue",
            fifo=True,
            queue_name=f"mermaid-{config.env_id}.fifo",
            content_based_deduplication=False,
            visibility_timeout=Duration.seconds(config.api.sqs_message_visibility),
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3, 
                queue=dead_letter_queue
            ),
        )

        # CloudWatch Alarm for Queue
        # Issue alarm when message is older than 15 mins in queue
        alarm_when_message_older_than = 15
        queue_alarm = cw.Alarm(
            self,
            "QueueAlarm",
            metric=queue.metric_approximate_age_of_oldest_message(
                statistic="Maximum",
                period=Duration.minutes(1),
            ),
            threshold=alarm_when_message_older_than,
            evaluation_periods=1,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cw.TreatMissingData.IGNORE,
        )

        # CloudWatch Alarm for DLQ
        dlq_alarm = cw.Alarm(
            self,
            "DLQAlarm",
            metric=queue.metric_approximate_number_of_messages_visible(
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

        queue_alarm.add_alarm_action(sns_action)
        queue_alarm.add_ok_action(sns_action)

        dlq_alarm.add_alarm_action(sns_action)
        dlq_alarm.add_ok_action(sns_action)

        # export the main queue
        self.queue = queue