from aws_cdk import CfnOutput, Duration, Stack, aws_iam as iam, aws_s3 as s3
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

        self.classifier_release_role = self._create_classifier_release_role(
            externalOidcProvider
        )

    def _create_classifier_release_role(
        self, oidc_provider: iam.OpenIdConnectProvider
    ) -> iam.Role:
        """Least-privilege role assumed by the mermaid-classifier release
        workflow (Issue #50) via GitHub OIDC.

        Reads a trained model from the project's SageMaker-Studio MLflow apps
        and publishes the portable artifact to mermaid-config/classifier/<vN>/.
        Trust is repo-wide (any ref in mermaid-classifier) — an accepted
        posture given the tightly-scoped permissions below.
        """
        role = iam.Role(
            self,
            "MermaidClassifierReleaseRole",
            role_name="mermaid-classifier-release-role",
            assumed_by=iam.WebIdentityPrincipal(
                identity_provider=oidc_provider.open_id_connect_provider_arn,
                conditions={
                    "StringEquals": {
                        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
                    },
                    "StringLike": {
                        "token.actions.githubusercontent.com:sub": (
                            "repo:data-mermaid/mermaid-classifier:*"
                        )
                    },
                },
            ),
            max_session_duration=Duration.hours(1),
        )

        # MLflow: liberal across the project's SageMaker-Studio MLflow apps.
        # sagemaker-mlflow exposes no resource-level ARNs, so '*' is required;
        # the sagemaker:* MLflow-app actions let the client resolve/auth the
        # mlflow-app tracking ARN. Mirrors the SageMaker launcher role.
        role.attach_inline_policy(
            iam.Policy(
                self,
                "ClassifierReleaseMlflowPolicy",
                statements=[
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=[
                            "sagemaker-mlflow:*",
                            "sagemaker:DescribeMlflowApp",
                            "sagemaker:ListMlflowApps",
                            "sagemaker:CreatePresignedMlflowAppUrl",
                        ],
                        resources=["*"],
                    ),
                ],
            )
        )

        # MLflow artifact store: read the model.pt + model.json written by
        # training. Artifacts live under s3://dev-datamermaid-sm-data/mlflow/.
        sm_data_bucket = s3.Bucket.from_bucket_arn(
            self,
            "ClassifierReleaseSmDataBucket",
            "arn:aws:s3:::dev-datamermaid-sm-data",
        )
        sm_data_bucket.grant_read(role, "mlflow/*")

        # mermaid-config: read the extractor weights (classifier/v1/...) and
        # write the per-version artifact (classifier/<vN>/...).
        mermaid_config_bucket = s3.Bucket.from_bucket_arn(
            self,
            "ClassifierReleaseConfigBucket",
            "arn:aws:s3:::mermaid-config",
        )
        mermaid_config_bucket.grant_read_write(role, "classifier/*")

        CfnOutput(
            self,
            "MermaidClassifierReleaseRoleArn",
            value=role.role_arn,
            description="IAM role assumed by the mermaid-classifier release workflow",
            export_name="MermaidClassifierReleaseRoleArn",
        )

        return role
