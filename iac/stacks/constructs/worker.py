from aws_cdk import (
    aws_applicationautoscaling as appscaling,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_logs as logs,
    aws_s3 as s3,
)
from constructs import Construct
from settings.settings import IMAGE_WORKER_MAX_TASKS, ProjectSettings
from stacks.constructs.adot import add_adot_sidecar
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
        visibility_timeout_seconds: int | None = None,
        log_group: logs.ILogGroup | None = None,
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
            visibility_timeout_seconds=visibility_timeout_seconds,
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
            # An explicit log group gives callers (e.g. a metric filter on this
            # worker's output) a stable reference; omitted, the pattern construct
            # auto-creates one that is retained (not deleted) on any rename.
            log_driver=(
                ecs.LogDrivers.aws_logs(stream_prefix=id, log_group=log_group)
                if log_group
                else None
            ),
            command=[
                "opentelemetry-instrument",
                "python",
                "manage.py",
                "simpleq_worker",
                "-n",
                queue_name,
            ],
            min_healthy_percent=0,
            min_scaling_capacity=1,
            max_scaling_capacity=IMAGE_WORKER_MAX_TASKS,
            # this defines how the service shall autoscale based on the
            # SQS queue's ApproximateNumberOfMessagesVisible metric
            scaling_steps=[
                # when <=10 messages, scale down
                appscaling.ScalingInterval(upper=100, change=-1),
                # when >=10 messages, scale up
                appscaling.ScalingInterval(lower=100, change=+1),
            ],
            capacity_provider_strategies=cluster.default_capacity_provider_strategy,
            circuit_breaker=ecs.DeploymentCircuitBreaker(enable=True, rollback=True),
        )
        # Allow workers to send messages.
        job_queue.queue.grant(
            worker_service.service.task_definition.task_role,
            "sqs:DeleteMessage",
            "sqs:SendMessage",
            "sqs:GetQueueAttributes",
            "sqs:GetQueueUrl",
        )

        # ADOT X-Ray sidecar
        add_adot_sidecar(worker_service.task_definition, "Worker")

        # allow worker access to public bucket
        public_bucket.grant_read_write(worker_service.task_definition.task_role)

        # exports
        self.queue = job_queue.queue
        self.dead_letter_queue = job_queue.dead_letter_queue
        self.service = worker_service.service
        self.task_definition = worker_service.task_definition
