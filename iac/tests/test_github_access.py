import aws_cdk as cdk
from aws_cdk.assertions import Match, Template
from stacks.github_access import GithubAccessStack


def _template():
    app = cdk.App()
    stack = GithubAccessStack(app, "gh-test", env=cdk.Environment(account="111111111111", region="us-east-1"))
    return Template.from_stack(stack)


def test_inference_push_role_exists_with_repo_scoped_trust():
    template = _template()
    template.has_resource_properties(
        "AWS::IAM::Role",
        Match.object_like({"RoleName": "mermaid-inference-image-push-role"}),
    )


def test_inference_push_policy_targets_the_repo():
    template = _template()
    template.has_resource_properties(
        "AWS::IAM::Policy",
        {
            "PolicyDocument": {
                "Statement": Match.array_with(
                    [Match.object_like({"Action": Match.array_with(["ecr:PutImage"])})]
                )
            }
        },
    )
