from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecr_assets as ecr_assets,
    aws_lambda,
    aws_lambda_event_sources as lambda_event_source,
    aws_s3 as s3,
    aws_iam as iam,
)
from constructs import Construct

from settings.settings import ProjectSettings
from stacks.constructs.queue import JobQueue


class LambdaWorker(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        config: ProjectSettings,
        vpc: ec2.IVpc,
        container_security_group: ec2.SecurityGroup,
        api_secrets: dict,  # TODO manage secrets.
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
            "LambdaWorker",
            config=config,
            queue_name=queue_name,
            fifo=fifo,
            email=email,
        )

        image = aws_lambda.DockerImageCode.from_image_asset(
            directory="../", file="Dockerfile", target="lambda_function"
        )


        # Lambda update_summary worker
        worker_function = aws_lambda.DockerImageFunction(
            self,
            "WorkerFunction",
            code=image,
            environment=environment,
            vpc=vpc,
            memory_size=config.api.sqs_memory,
            security_groups=[container_security_group],
            vpc_subnets=ec2.SubnetSelection(
                subnets=vpc.select_subnets(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS).subnets
            ),
        )
        secret_arns = []
        for _, secret in api_secrets.items():
            secret.grant_read(worker_function)
            secret_arns.append(secret.arn)


        # Attach the policy to the Lambda's execution role to allow access to Secrets Manager
        worker_function.add_to_role_policy(
            statement=iam.PolicyStatement(
                actions=["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"],  # Allow access to the Secret
                resources=secret_arns,  # Specify which secret the Lambda can access
            )
        )
        # TODO: limit number of functions

        # Create an SQS event source for Lambda
        sqs_event_source = lambda_event_source.SqsEventSource(job_queue.queue)

        # Add SQS event source to the Lambda function
        worker_function.add_event_source(sqs_event_source)

        # Allow workers to send messages.
        job_queue.queue.grant(
            worker_function,
            "sqs:DeleteMessage",
            "sqs:SendMessage",
            "sqs:GetQueueAttributes",
            "sqs:GetQueueUrl",
        )

        # allow worker access to public bucket
        public_bucket.grant_read_write(worker_function)

        # exports
        self.queue = job_queue.queue
        self.function = worker_function
