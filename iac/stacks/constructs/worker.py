from aws_cdk import (
    aws_applicationautoscaling as appscaling,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_s3 as s3,
)
from constructs import Construct
from settings.settings import ProjectSettings
from stacks.constructs.queue import JobQueue


class QueueWorker(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        config: ProjectSettings,
        cluster: ecs.Cluster,
        image_asset: ecs.ContainerImage,
        api_secrets: dict,
        environment: dict,
        public_bucket: s3.Bucket,
        queue_name: str,
        fifo: bool = False,
        email: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        job_queue = JobQueue(
            self,
            "ECSWorker",
            config=config,
            queue_name=queue_name,
            fifo=fifo,
            email=email,
        )

        worker_service = ecs_patterns.QueueProcessingEc2Service(
            self,
            "Worker",
            cluster=cluster,
            queue=job_queue.queue,
            image=image_asset,
            cpu=config.api.sqs_cpu,
            memory_limit_mib=config.api.sqs_memory,
            secrets=api_secrets,
            environment=environment,
            command=["python", "manage.py", "simpleq_worker", "-n", queue_name],
            min_scaling_capacity=1,
            max_scaling_capacity=3,
            # this defines how the service shall autoscale based on the
            # SQS queue's ApproximateNumberOfMessagesVisible metric
            scaling_steps=[
                # when <=10 messages, scale down
                appscaling.ScalingInterval(upper=10, change=-1),
                # when >=10 messages, scale up
                appscaling.ScalingInterval(lower=10, change=+1),
            ],
            capacity_provider_strategies=[
                ecs.CapacityProviderStrategy(
                    capacity_provider="mermaid-api-infra-common-AsgCapacityProvider760D11D9-iqzBF6LfX313",
                    weight=100,
                )
            ],
        )
        # Allow workers to send messages.
        job_queue.queue.grant(
            worker_service.service.task_definition.task_role,
            "sqs:DeleteMessage",
            "sqs:SendMessage",
            "sqs:GetQueueAttributes",
            "sqs:GetQueueUrl",
        )

        # allow worker access to public bucket
        public_bucket.grant_read_write(worker_service.task_definition.task_role)

        # exports
        self.queue = job_queue.queue
        self.service = worker_service.service
        self.task_definition = worker_service.task_definition
