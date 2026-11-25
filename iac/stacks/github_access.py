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
                        # Phase 1 (card 2261): scope the admin role to the repos that
                        # actually deploy through it, instead of the previous
                        # "mermaid-*", which let any of the ~23 data-mermaid/mermaid-*
                        # repos (including archived and private ones) assume an
                        # AdministratorAccess role. mermaid-webapp and mermaid-dash-v2
                        # run `cdk deploy` into the same account (554812291621) via this
                        # same role (their CDK_DEPLOY_ROLE secret; neither defines its own
                        # deploy role), so they must stay on the allowlist or their
                        # deploys break. classifier/inference/segmentation use their own
                        # dedicated roles; every other mermaid-* repo touches no AWS.
                        # Keep this list in sync when a repo starts/stops deploying here.
                        #
                        # Phase 2 (card 2261): each subject is pinned to the deploy job's
                        # actual OIDC `sub`, so a PR (subject "...:pull_request") can no
                        # longer assume this AdministratorAccess role — PR CI uses
                        # github-pr-readonly-role instead. The subject differs per repo
                        # because of how each deploy job is configured:
                        #   - mermaid-api / mermaid-webapp set a GitHub `environment:` on the
                        #     deploy job, so the subject is "...:environment:<env>".
                        #     (webapp's prod environment is named "production", not "prod".)
                        #   - mermaid-dash-v2's deploy job sets no GitHub environment (its
                        #     `environment` input is only a vite/name string), so the subject
                        #     is "...:ref:<git ref>": develop for dev, a v*.*.* tag for prod.
                        # Update a repo's entry here if it changes how its deploy job runs.
                        "token.actions.githubusercontent.com:sub": [
                            "repo:data-mermaid/mermaid-api:environment:dev",
                            "repo:data-mermaid/mermaid-api:environment:prod",
                            "repo:data-mermaid/mermaid-webapp:environment:dev",
                            "repo:data-mermaid/mermaid-webapp:environment:production",
                            "repo:data-mermaid/mermaid-dash-v2:ref:refs/heads/develop",
                            "repo:data-mermaid/mermaid-dash-v2:ref:refs/tags/v*",
                        ]
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

        # Read-only role for PR CI (pr.yml `cdk synth`/`cdk diff --method=template`), so PRs
        # never assume the AdministratorAccess role above. Trusted for the pull_request
        # context of every repo that runs this CI (mermaid-api, mermaid-webapp,
        # mermaid-dash-v2 — same allowlist as the admin role). Permissions are a custom
        # least-privilege policy, NOT the AWS managed ReadOnlyAccess (which would also grant
        # s3:Get* on the DB-backup buckets, lambda:GetFunction env vars, ssm:GetParameter
        # SecureStrings, and logs:GetLogEvents to any PR in these repos).
        #
        # NOTE: mermaid-webapp's PR job currently runs in `environment: dev`, so its subject
        # is ":environment:dev", not ":pull_request" — it will only match this role once that
        # `environment:` is removed from its pr.yml (card 2277, phase-2 step 2). Listing it
        # here now is harmless.
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
                        "token.actions.githubusercontent.com:sub": [
                            "repo:data-mermaid/mermaid-api:pull_request",
                            "repo:data-mermaid/mermaid-webapp:pull_request",
                            "repo:data-mermaid/mermaid-dash-v2:pull_request",
                        ]
                    },
                },
            ),
            max_session_duration=Duration.hours(1),
        )
        # Exactly what `cdk diff --method=template` needs: read deployed templates/stacks
        # and the CDK bootstrap version parameter. No change-set creation, no bootstrap
        # deploy-role assumption, no data-plane reads. CloudFormation read actions are not
        # resource-scopable across all stacks, so they use Resource "*".
        self.github_pr_read_role.attach_inline_policy(
            iam.Policy(
                self,
                "GithubPrReadPolicy",
                statements=[
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=[
                            "cloudformation:Describe*",
                            "cloudformation:GetTemplate",
                            "cloudformation:GetTemplateSummary",
                            "cloudformation:List*",
                        ],
                        resources=["*"],
                    ),
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=["ssm:GetParameter", "ssm:GetParameters"],
                        resources=[
                            f"arn:aws:ssm:{self.region}:{self.account}:parameter/cdk-bootstrap/*"
                        ],
                    ),
                ],
            )
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

        repo_arn = f"arn:aws:ecr:{self.region}:{self.account}:repository/mermaid-inference-pyspacer"
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
