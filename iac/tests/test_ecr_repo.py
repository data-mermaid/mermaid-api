import aws_cdk as cdk
from aws_cdk.assertions import Template
from stacks.common import CommonStack


def _template():
    app = cdk.App()
    stack = CommonStack(app, "common-test", env=cdk.Environment(account="111111111111", region="us-east-1"))
    return Template.from_stack(stack)


def test_inference_ecr_repo_exists_and_is_immutable():
    template = _template()
    template.has_resource_properties(
        "AWS::ECR::Repository",
        {
            "RepositoryName": "mermaid-inference-pyspacer",
            "ImageTagMutability": "IMMUTABLE",
        },
    )
