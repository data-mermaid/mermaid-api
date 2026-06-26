import json

import aws_cdk as cdk
from aws_cdk.assertions import Match, Template
from stacks.github_access import GithubAccessStack


def _inference_push_policy(template):
    """The single inline policy attached to MermaidInferenceImagePushRole.

    Scoping the action assertions to this specific policy (rather than scanning
    every AWS::IAM::Policy) ensures they fail if InferenceImagePushPolicy itself
    regresses — they can't be satisfied by some unrelated policy that happens to
    grant the same ECR action.
    """
    roles = {
        lid: r
        for lid, r in template.find_resources("AWS::IAM::Role").items()
        if r["Properties"].get("RoleName") == "mermaid-inference-image-push-role"
    }
    assert len(roles) == 1, f"expected exactly one push role, found {list(roles)}"
    (role_lid,) = roles
    policies = [
        p
        for p in template.find_resources("AWS::IAM::Policy").values()
        if any(
            isinstance(ref, dict) and ref.get("Ref") == role_lid
            for ref in p["Properties"].get("Roles", [])
        )
    ]
    assert len(policies) == 1, f"expected one policy on the push role, found {len(policies)}"
    return policies[0]


def _statements_with(template, action):
    """Statements of the inference push policy granting `action`."""
    out = []
    for stmt in _inference_push_policy(template)["Properties"]["PolicyDocument"]["Statement"]:
        actions = stmt["Action"] if isinstance(stmt["Action"], list) else [stmt["Action"]]
        if action in actions:
            out.append(stmt)
    return out


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


def test_inference_push_role_trust_scoped_to_main_and_release_tags():
    template = _template()
    # Trust must evaluate the GitHub sub claim (required for shared OIDC
    # providers) AND scope it to the refs that publish — main + v* tags.
    template.has_resource_properties(
        "AWS::IAM::Role",
        {
            "RoleName": "mermaid-inference-image-push-role",
            "AssumeRolePolicyDocument": {
                "Statement": Match.array_with(
                    [
                        Match.object_like(
                            {
                                "Condition": {
                                    "StringLike": {
                                        "token.actions.githubusercontent.com:sub": [
                                            "repo:data-mermaid/mermaid-inference:ref:refs/heads/main",
                                            "repo:data-mermaid/mermaid-inference:ref:refs/tags/v*",
                                        ]
                                    },
                                    "StringEquals": {
                                        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
                                    },
                                }
                            }
                        )
                    ]
                )
            },
        },
    )


def test_inference_push_policy_is_scoped_to_the_repo():
    template = _template()
    # The push actions must target the mermaid-inference-pyspacer repo ARN —
    # never "*" (all repos) and never a different repo. Fails if the resource is
    # widened or repointed. (ecr:GetAuthorizationToken on "*" is a separate
    # statement and is required by the ECR API — see GetAuthorizationToken test.)
    push_stmts = _statements_with(template, "ecr:PutImage")
    assert push_stmts, "no statement grants ecr:PutImage"
    for stmt in push_stmts:
        assert stmt["Resource"] != "*", "push actions must not be granted on '*'"
        assert "mermaid-inference-pyspacer" in json.dumps(stmt["Resource"])


def test_get_authorization_token_is_account_level():
    template = _template()
    # The one action that genuinely cannot be resource-scoped stays on "*".
    token_stmts = _statements_with(template, "ecr:GetAuthorizationToken")
    assert token_stmts
    assert any(s["Resource"] == "*" for s in token_stmts)
