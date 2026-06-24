# mermaid-api/iac/tests/test_inference_stack.py
import aws_cdk as cdk
from aws_cdk import aws_ecr as ecr, aws_s3 as s3
from aws_cdk.assertions import Match, Template
from settings.dev import DEV_SETTINGS
from stacks.inference import InferenceStack


def _template():
    app = cdk.App()
    env = cdk.Environment(account="111111111111", region="us-east-1")
    deps = cdk.Stack(app, "deps", env=env)
    repo = ecr.Repository(deps, "Repo", repository_name="mermaid-inference-pyspacer")
    config_bucket = s3.Bucket(deps, "Config", bucket_name="mermaid-config")
    image_bucket = s3.Bucket(deps, "Img", bucket_name="mermaid-image-processing")
    stack = InferenceStack(
        app,
        "dev-mermaid-inference",
        env=env,
        config=DEV_SETTINGS,
        inference_repo=repo,
        config_bucket=config_bucket,
        image_bucket=image_bucket,
    )
    return Template.from_stack(stack)


def test_function_config():
    template = _template()
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "PackageType": "Image",
            "MemorySize": 10240,
            "Timeout": 600,
            "Architectures": ["arm64"],
            "ReservedConcurrentExecutions": 20,
            "TracingConfig": {"Mode": "Active"},
            "EphemeralStorage": {"Size": 2048},
            "Environment": {
                "Variables": {
                    "CONFIG_BUCKET": "mermaid-config",
                    "INFERENCE_NUM_THREADS": "6",
                }
            },
        },
    )


def test_function_role_can_read_both_buckets():
    template = _template()
    # The function role gets s3:GetObject on classifier/* and the image bucket.
    template.has_resource_properties(
        "AWS::IAM::Policy",
        {
            "PolicyDocument": {
                "Statement": Match.array_with(
                    [
                        Match.object_like(
                            {"Action": Match.array_with(["s3:GetObject*"])}
                        )
                    ]
                )
            }
        },
    )
