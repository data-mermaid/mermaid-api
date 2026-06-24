# mermaid-api/iac/stacks/inference.py
from aws_cdk import (
    Duration,
    Size,
    Stack,
    aws_ecr as ecr,
    aws_lambda as lambda_,
    aws_s3 as s3,
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
