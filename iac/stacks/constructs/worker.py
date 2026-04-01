from aws_cdk import (
    aws_applicationautoscaling as appscaling,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_iam as iam,
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
            command=["opentelemetry-instrument", "python", "manage.py", "simpleq_worker", "-n", queue_name],
            min_scaling_capacity=1,
            max_scaling_capacity=3,
            # this defines how the service shall autoscale based on the
            # SQS queue's ApproximateNumberOfMessagesVisible metric
            scaling_steps=[
                # when <=10 messages, scale down
                appscaling.ScalingInterval(upper=100, change=-1),
                # when >=10 messages, scale up
                appscaling.ScalingInterval(lower=100, change=+1),
            ],
            capacity_provider_strategies=cluster.default_capacity_provider_strategy,
            # circuit_breaker=ecs.DeploymentCircuitBreaker(enable=True, rollback=True),
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
        worker_service.task_definition.add_container(
            "AdotCollector",
            image=ecs.ContainerImage.from_registry(
                "public.ecr.aws/aws-observability/aws-otel-collector:latest"
            ),
            cpu=32,
            memory_limit_mib=256,
            essential=False,
            command=["--config=/etc/ecs/ecs-xray.yaml"],
            port_mappings=[
                ecs.PortMapping(container_port=4317, protocol=ecs.Protocol.TCP),
                ecs.PortMapping(container_port=4318, protocol=ecs.Protocol.TCP),
                ecs.PortMapping(container_port=2000, protocol=ecs.Protocol.UDP),
            ],
            logging=ecs.LogDrivers.aws_logs(stream_prefix="worker-adot"),
        )
        worker_service.task_definition.task_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AWSXRayDaemonWriteAccess")
        )

        # allow worker access to public bucket
        public_bucket.grant_read_write(worker_service.task_definition.task_role)

        # exports
        self.queue = job_queue.queue
        self.dead_letter_queue = job_queue.dead_letter_queue
        self.service = worker_service.service
        self.task_definition = worker_service.task_definition
