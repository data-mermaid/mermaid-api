from aws_cdk import CfnOutput, Duration, Stack, aws_iam as iam
from constructs import Construct


class GithubAccessStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        externalOidcProvider = iam.OpenIdConnectProvider(
            self,
            "GithubOIDCProvider",
            url="https://token.actions.githubusercontent.com",
            client_ids=["sts.amazonaws.com"],
        )

        self.github_access_role = iam.Role(
            self,
            "GithubAccessRole",
            assumed_by=iam.WebIdentityPrincipal(
                identity_provider=externalOidcProvider.open_id_connect_provider_arn,
                conditions={
                    "StringEquals": {
                        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
                    },
                    "StringLike": {
                        "token.actions.githubusercontent.com:sub": "repo:data-mermaid/mermaid-*"
                    },
                },
            ),
            max_session_duration=Duration.hours(3),
        )

        self.github_access_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AdministratorAccess")
        )

        self.inference_image_push_role = self._create_inference_image_push_role(
            externalOidcProvider
        )

    def _create_inference_image_push_role(
        self, oidc_provider: iam.OpenIdConnectProvider
    ) -> iam.Role:
        """Least-privilege role assumed by the mermaid-inference build-push
        workflow (mermaid-classifier issue #53) via GitHub OIDC.

        Pushes the pyspacer inference image to the mermaid-inference-pyspacer
        ECR repo. Trust is scoped to the refs that actually publish — the
        `main` branch and `v*` release tags (the build-push workflow's only
        triggers) — so feature branches and PRs cannot assume this role.
        """
        role = iam.Role(
            self,
            "MermaidInferenceImagePushRole",
            role_name="mermaid-inference-image-push-role",
            assumed_by=iam.WebIdentityPrincipal(
                identity_provider=oidc_provider.open_id_connect_provider_arn,
                conditions={
                    "StringEquals": {
                        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
                    },
                    "StringLike": {
                        "token.actions.githubusercontent.com:sub": [
                            "repo:data-mermaid/mermaid-inference:ref:refs/heads/main",
                            "repo:data-mermaid/mermaid-inference:ref:refs/tags/v*",
                        ]
                    },
                },
            ),
            max_session_duration=Duration.hours(1),
        )

        repo_arn = (
            f"arn:aws:ecr:{self.region}:{self.account}:"
            "repository/mermaid-inference-pyspacer"
        )
        role.attach_inline_policy(
            iam.Policy(
                self,
                "InferenceImagePushPolicy",
                statements=[
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=["ecr:GetAuthorizationToken"],
                        resources=["*"],  # required: not resource-scopable
                    ),
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=[
                            "ecr:BatchCheckLayerAvailability",
                            "ecr:InitiateLayerUpload",
                            "ecr:UploadLayerPart",
                            "ecr:CompleteLayerUpload",
                            "ecr:PutImage",
                            "ecr:BatchGetImage",
                        ],
                        resources=[repo_arn],
                    ),
                ],
            )
        )

        CfnOutput(
            self,
            "MermaidInferenceImagePushRoleArn",
            value=role.role_arn,
            description="IAM role assumed by the mermaid-inference build-push workflow",
            export_name="MermaidInferenceImagePushRoleArn",
        )

        return role
