import aws_cdk as cdk
from aws_cdk.assertions import Match, Template
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
            # Part of the repo's security contract — a regression that disables
            # scanning must fail here.
            "ImageScanningConfiguration": {"ScanOnPush": True},
        },
    )


def test_inference_ecr_repo_lifecycle_expires_only_untagged():
    template = _template()
    # The lifecycle policy must expire UNTAGGED images only — never count-prune
    # tagged releases, whose digests are pinned by deployed Lambdas.
    template.has_resource_properties(
        "AWS::ECR::Repository",
        {
            "RepositoryName": "mermaid-inference-pyspacer",
            "LifecyclePolicy": {
                "LifecyclePolicyText": Match.string_like_regexp(
                    r'"tagStatus":\s*"untagged"'
                ),
            },
        },
    )
