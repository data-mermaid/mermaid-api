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
                        # Phase 1 (card 2261): scope the admin role to this repo only. The
                        # previous "mermaid-*" let any data-mermaid repo's workflow assume
                        # it. Still allows any ref/PR of mermaid-api so pr.yml (which today
                        # assumes this role) keeps working.
                        #
                        # This is not a fork-PR boundary: a fork PR against this repo gets
                        # the subject "repo:data-mermaid/mermaid-api:pull_request", which
                        # matches. GitHub's fork-PR limits (no secrets, read-only token by
                        # default) are what stop a fork from assuming this role.
                        #
                        # Phase 2 (follow-up, AFTER the read-only role below is deployed):
                        # pin this to ":environment:dev"/":environment:prod" and point
                        # pr.yml at github-pr-readonly-role, so PRs can no longer assume the
                        # admin role. Doing both now would break PR CI, because the
                        # read-only role does not exist until this stack is deployed.
                        "token.actions.githubusercontent.com:sub": "repo:data-mermaid/mermaid-api:*"
                    },
                },
            ),
            max_session_duration=Duration.hours(3),
        )

        # NOTE (card 2261): this role runs `cdk deploy` for every stack, so it needs
        # broad permissions; AdministratorAccess is kept for now. Scoping the permissions
        # safely means migrating to CDK bootstrap deploy (`cdk deploy --role-arn
        # <cfn-exec-role>`) so this role only needs sts:AssumeRole on the cdk-* roles - a
        # separate change that must be validated against a real deploy. The trust narrowing
        # above already removes the cross-repo assumption vector.
        self.github_access_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AdministratorAccess")
        )

        # Read-only role for PR CI (pr.yml `cdk synth`/`cdk diff`), created now so a
        # phase-2 change can point pr.yml at it and pin the admin role away from PRs. Only
        # ReadOnlyAccess; trusted for the pull_request context.
        self.github_pr_read_role = iam.Role(
            self,
            "GithubPrReadRole",
            role_name="github-pr-readonly-role",
            assumed_by=iam.WebIdentityPrincipal(
                identity_provider=externalOidcProvider.open_id_connect_provider_arn,
                conditions={
                    "StringEquals": {
                        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
                    },
                    "StringLike": {
                        "token.actions.githubusercontent.com:sub": (
                            "repo:data-mermaid/mermaid-api:pull_request"
                        )
                    },
                },
            ),
            max_session_duration=Duration.hours(1),
        )
        self.github_pr_read_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("ReadOnlyAccess")
        )

        self.inference_image_push_role = self._create_inference_image_push_role(
            externalOidcProvider
        )

        self.classifier_release_role = self._create_classifier_release_role(externalOidcProvider)

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
            f"arn:aws:ecr:{self.region}:{self.account}:" "repository/mermaid-inference-pyspacer"
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

    def _create_classifier_release_role(self, oidc_provider: iam.OpenIdConnectProvider) -> iam.Role:
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
        #
        # sagemaker:CallMlflowAppApi is the data-plane action that authorizes
        # REST calls (search_experiments, artifact-URI resolution, ...) against
        # an mlflow-app resource. The sagemaker-mlflow:* namespace only governs
        # the older MLflow *tracking servers*, so without CallMlflowAppApi the
        # SigV4-signed REST calls to an mlflow-app 403 ("Request is not
        # authorized") even though sagemaker-mlflow:* is granted.
        role.attach_inline_policy(
            iam.Policy(
                self,
                "ClassifierReleaseMlflowPolicy",
                statements=[
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=[
                            "sagemaker-mlflow:*",
                            "sagemaker:CallMlflowAppApi",
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
