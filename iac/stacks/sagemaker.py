import aws_cdk as cdk
from aws_cdk import (
    CfnOutput,
    aws_ec2 as ec2,
    aws_ecr as ecr,
    aws_ecs as ecs,
    aws_iam as iam,
    aws_s3 as s3,
    aws_sagemaker as sm,
)
from constructs import Construct
from settings.settings import ProjectSettings


class SagemakerStack(cdk.Stack):
    """
    A CloudFormation stack for provisioning AWS SageMaker resources.
    This stack sets up the necessary infrastructure for SageMaker projects, including:
    - IAM roles for SageMaker execution.
    - S3 buckets for storing SageMaker code and data.
    - SageMaker Studio domain.
    It integrates with an existing ECS cluster to fetch VPC and subnet information.
    """

    def __init__(
        self,
        scope: Construct,
        id: str,
        config: ProjectSettings,
        cluster: ecs.Cluster,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        self.prefix = config.env_id

        # Fetch VPC information
        self.vpc = cluster.vpc
        private_subnet_ids = [
            private_subnet.subnet_id for private_subnet in self.vpc.private_subnets
        ]

        # Role for SageMaker jobs and the MLflow Apps
        self.sm_execution_role = self.create_execution_role()

        # Role for the Studio web UI (SSO users)
        self.sm_studio_role = self.create_studio_role()

        # Create S3 bucket for SageMaker code sources
        self.sm_sources_bucket = self.create_sm_sources_bucket()

        CfnOutput(
            self,
            f"{self.prefix}SourcesBucketName",
            value=self.sm_sources_bucket.bucket_name,
            description="SageMaker Sources Bucket Name",
            export_name=f"{self.prefix}-SourcesBucketName",
        )

        # Jobs read staged datasets and manifests. Staging writes come from
        # operator machines, not from jobs.
        self.sm_sources_bucket.grant_read(self.sm_execution_role)

        # Create S3 bucket for SageMaker data
        self.sm_data_bucket = self.create_data_bucket()

        self.sm_data_bucket.grant_read_write(self.sm_execution_role)

        # Create immutable S3 bucket for versioned image classification datasets
        self.ic_datasets_bucket = self.create_ic_datasets_bucket()

        self.ic_datasets_bucket.grant_read(self.sm_execution_role)

        CfnOutput(
            self,
            f"{self.prefix}ICDatasetsBucketName",
            value=self.ic_datasets_bucket.bucket_name,
            description="Image Classification Datasets Bucket Name",
            export_name=f"{self.prefix}-ICDatasetsBucketName",
        )

        # Training jobs read the released feature-extractor weights. Releases
        # are written from outside SageMaker, so jobs only need read access.
        self.mermaid_config = s3.Bucket.from_bucket_arn(
            self,
            f"{self.prefix}MermaidConfigBucket",
            bucket_arn="arn:aws:s3:::mermaid-config",
        )

        self.mermaid_config.grant_read(self.sm_execution_role, "classifier/*")

        # MERMAID training images and annotations. The bucket is in another
        # account, so the role needs an identity-side grant even though reads
        # are public.
        self.coral_reef_training = s3.Bucket.from_bucket_arn(
            self,
            f"{self.prefix}CoralReefTrainingBucket",
            bucket_arn="arn:aws:s3:::coral-reef-training",
        )

        self.coral_reef_training.grant_read(self.sm_execution_role, "mermaid/*")

        # Artifact store of the mermaid-mlflow MLflow App, which runs as this role.
        self.mermaid_mlflow = s3.Bucket.from_bucket_arn(
            self,
            f"{self.prefix}MermaidMlflowBucket",
            bucket_arn="arn:aws:s3:::mermaid-mlflow",
        )

        self.mermaid_mlflow.grant_read_write(self.sm_execution_role)

        # Feature-vector bucket used by two mermaid-classifier launchers:
        # the feature-extraction ProcessingJob writes per-source .fv files
        # and annotations.csv into it; the training launcher reads them back.
        # Hence read+write, not read-only.
        self.coralnet_feature_vectors = s3.Bucket.from_bucket_arn(
            self,
            f"{self.prefix}CoralnetFeatureVectorsBucket",
            bucket_arn="arn:aws:s3:::2605-coralnet-public-sources",
        )

        self.coralnet_feature_vectors.grant_read_write(self.sm_execution_role)

        # ECR repositories + shared IAM role for the mermaid-* SageMaker
        # launchers (both classifier and segmentation, both Training and
        # Processing jobs). See iac/sagemaker-launcher-convention.md for
        # the cross-repo contract.
        self.classifier_jobs_repo = self.create_classifier_jobs_repo()
        self.segmentation_jobs_repo = self.create_segmentation_jobs_repo()
        self.sagemaker_launcher_role = self.create_sagemaker_launcher_role()

        self.security_group = ec2.SecurityGroup(
            self,
            f"{self.prefix}SagemakerSecurityGroup",
            vpc=self.vpc,
            allow_all_outbound=True,
            description="Security group for SageMaker Studio",
        )

        # Create SageMaker Studio domain
        self.domain = sm.CfnDomain(
            self,
            f"{self.prefix}SagemakerDomain",
            auth_mode="SSO",
            domain_name=f"{self.prefix}-SG-Project",
            default_user_settings=sm.CfnDomain.UserSettingsProperty(
                execution_role=self.sm_studio_role.role_arn,
                security_groups=[
                    self.security_group.security_group_id,
                ],
                # Studio is used to monitor jobs and open MLflow, not to run
                # code. Hiding apps tidies the UI; the studio role's IAM
                # policy is what blocks them.
                studio_web_portal_settings=sm.CfnDomain.StudioWebPortalSettingsProperty(
                    hidden_app_types=[
                        "JupyterLab",
                        "CodeEditor",
                        "JupyterServer",
                        "RStudioServerPro",
                        "Canvas",
                    ],
                ),
            ),
            app_network_access_type="VpcOnly",
            vpc_id=self.vpc.vpc_id,
            subnet_ids=private_subnet_ids,
            domain_settings=sm.CfnDomain.DomainSettingsProperty(
                docker_settings=sm.CfnDomain.DockerSettingsProperty(
                    enable_docker_access="DISABLED",
                ),
                security_group_ids=[
                    self.security_group.security_group_id,
                ],
            ),
            default_space_settings=sm.CfnDomain.DefaultSpaceSettingsProperty(
                execution_role=self.sm_studio_role.role_arn,
                space_storage_settings=sm.CfnDomain.DefaultSpaceStorageSettingsProperty(
                    default_ebs_storage_settings=sm.CfnDomain.DefaultEbsStorageSettingsProperty(
                        default_ebs_volume_size_in_gb=50,
                        maximum_ebs_volume_size_in_gb=1000,
                    ),
                ),
                jupyter_lab_app_settings=sm.CfnDomain.JupyterLabAppSettingsProperty(
                    default_resource_spec=sm.CfnDomain.ResourceSpecProperty(
                        instance_type="ml.t3.medium",
                    ),
                ),
                security_groups=[
                    self.security_group.security_group_id,
                ],
            ),
        )

        CfnOutput(
            self,
            f"{self.prefix}SagemakerDomainUrl",
            value=self.domain.attr_url,
            description="SageMaker Domain URL",
            export_name=f"{self.prefix}-SagemakerDomainUrl",
        )

    def create_execution_role(self) -> iam.Role:
        """Role that SageMaker jobs and the MLflow Apps run as.

        The mermaid-* launchers pass this role as the RoleArn of Training and
        Processing jobs, and the MLflow Apps use it as their service role.
        S3 access is granted per bucket in __init__. The Studio web UI uses
        its own role (create_studio_role).
        """
        role = iam.Role(
            self,
            f"{self.prefix}SagemakerExecutionRole",
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
            role_name=f"{self.prefix}-sm-execution-role",
        )

        sm_arn = f"arn:aws:sagemaker:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}"
        logs_arn = f"arn:aws:logs:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:log-group"

        role.attach_inline_policy(
            iam.Policy(
                self,
                "SagemakerJobRuntimePolicy",
                statements=[
                    # GetAuthorizationToken must be on '*' (AWS rule).
                    iam.PolicyStatement(
                        sid="EcrAuth",
                        effect=iam.Effect.ALLOW,
                        actions=["ecr:GetAuthorizationToken"],
                        resources=["*"],
                    ),
                    iam.PolicyStatement(
                        sid="EcrPull",
                        effect=iam.Effect.ALLOW,
                        actions=[
                            "ecr:BatchGetImage",
                            "ecr:GetDownloadUrlForLayer",
                            "ecr:BatchCheckLayerAvailability",
                        ],
                        resources=[
                            f"arn:aws:ecr:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}"
                            ":repository/mermaid-*-jobs",
                        ],
                    ),
                    iam.PolicyStatement(
                        sid="JobLogs",
                        effect=iam.Effect.ALLOW,
                        actions=[
                            "logs:CreateLogGroup",
                            "logs:CreateLogStream",
                            "logs:PutLogEvents",
                            "logs:DescribeLogStreams",
                        ],
                        resources=[
                            f"{logs_arn}:/aws/sagemaker/TrainingJobs",
                            f"{logs_arn}:/aws/sagemaker/TrainingJobs:*",
                            f"{logs_arn}:/aws/sagemaker/ProcessingJobs",
                            f"{logs_arn}:/aws/sagemaker/ProcessingJobs:*",
                        ],
                    ),
                    # PutMetricData has no resource-level ARNs; the namespace
                    # condition limits it to SageMaker job metrics.
                    iam.PolicyStatement(
                        sid="JobMetrics",
                        effect=iam.Effect.ALLOW,
                        actions=["cloudwatch:PutMetricData"],
                        resources=["*"],
                        conditions={"StringLike": {"cloudwatch:namespace": "/aws/sagemaker/*"}},
                    ),
                    # MLflow Apps authorize tracking calls with
                    # sagemaker:CallMlflowAppApi; sagemaker-mlflow:* only
                    # covers the older tracking servers.
                    iam.PolicyStatement(
                        sid="MlflowLogging",
                        effect=iam.Effect.ALLOW,
                        actions=["sagemaker:CallMlflowAppApi"],
                        resources=[f"{sm_arn}:mlflow-app/*"],
                    ),
                    # Hugging Face token read by the segmentation training
                    # entrypoint (HF_TOKEN_SECRET_ID).
                    iam.PolicyStatement(
                        sid="HfTokenSecret",
                        effect=iam.Effect.ALLOW,
                        actions=["secretsmanager:GetSecretValue"],
                        resources=[
                            f"arn:aws:secretsmanager:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}"
                            ":secret:mermaid-segmentation/hf-token-*",
                        ],
                    ),
                ],
            )
        )

        CfnOutput(
            self,
            f"{self.prefix}SagemakerExecutionRoleArn",
            value=role.role_arn,
            description="SageMaker Execution Role ARN",
            export_name=f"{self.prefix}-SagemakerExecutionRoleArn",
        )

        return role

    def create_studio_role(self) -> iam.Role:
        """Role for the Studio web UI.

        The domain uses SSO, so the browser calls AWS as the user profile's
        execution role. Studio is used to monitor training jobs, read their
        logs and open MLflow. The role cannot create spaces or apps, and has
        no S3 access.
        """
        role = iam.Role(
            self,
            f"{self.prefix}SagemakerStudioRole",
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
            role_name=f"{self.prefix}-sm-studio-role",
        )

        sm_arn = f"arn:aws:sagemaker:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}"
        logs_arn = f"arn:aws:logs:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:log-group"

        role.attach_inline_policy(
            iam.Policy(
                self,
                "SagemakerStudioUiPolicy",
                statements=[
                    # Studio home page.
                    iam.PolicyStatement(
                        sid="StudioShellDescribe",
                        effect=iam.Effect.ALLOW,
                        actions=[
                            "sagemaker:DescribeDomain",
                            "sagemaker:DescribeUserProfile",
                            "sagemaker:DescribeSpace",
                            "sagemaker:DescribeApp",
                        ],
                        resources=[
                            f"{sm_arn}:domain/*",
                            f"{sm_arn}:user-profile/*",
                            f"{sm_arn}:space/*",
                            f"{sm_arn}:app/*",
                        ],
                    ),
                    # List and Search actions have no resource-level ARNs.
                    iam.PolicyStatement(
                        sid="StudioList",
                        effect=iam.Effect.ALLOW,
                        actions=[
                            "sagemaker:ListSpaces",
                            "sagemaker:ListApps",
                            "sagemaker:ListTrainingJobs",
                            "sagemaker:ListProcessingJobs",
                            "sagemaker:Search",
                            "sagemaker:ListMlflowApps",
                        ],
                        resources=["*"],
                    ),
                    iam.PolicyStatement(
                        sid="JobDescribe",
                        effect=iam.Effect.ALLOW,
                        actions=[
                            "sagemaker:DescribeTrainingJob",
                            "sagemaker:DescribeProcessingJob",
                            "sagemaker:ListTags",
                        ],
                        resources=[
                            f"{sm_arn}:training-job/*",
                            f"{sm_arn}:processing-job/*",
                        ],
                    ),
                    # DescribeLogGroups must be on '*' (AWS rule).
                    iam.PolicyStatement(
                        sid="JobLogGroups",
                        effect=iam.Effect.ALLOW,
                        actions=["logs:DescribeLogGroups"],
                        resources=["*"],
                    ),
                    iam.PolicyStatement(
                        sid="JobLogRead",
                        effect=iam.Effect.ALLOW,
                        actions=[
                            "logs:DescribeLogStreams",
                            "logs:GetLogEvents",
                            "logs:FilterLogEvents",
                        ],
                        resources=[
                            f"{logs_arn}:/aws/sagemaker/*",
                            f"{logs_arn}:/aws/sagemaker/*:*",
                        ],
                    ),
                    iam.PolicyStatement(
                        sid="MlflowOpen",
                        effect=iam.Effect.ALLOW,
                        actions=[
                            "sagemaker:DescribeMlflowApp",
                            "sagemaker:CreatePresignedMlflowAppUrl",
                            "sagemaker:CallMlflowAppApi",
                        ],
                        resources=[f"{sm_arn}:mlflow-app/*"],
                    ),
                ],
            )
        )

        CfnOutput(
            self,
            f"{self.prefix}SagemakerStudioRoleArn",
            value=role.role_arn,
            description="SageMaker Studio UI Role ARN",
            export_name=f"{self.prefix}-SagemakerStudioRoleArn",
        )

        return role

    def create_classifier_jobs_repo(self) -> ecr.Repository:
        """ECR repository for the mermaid-classifier SageMaker job image.

        Tag-based separation (`:training-latest`, `:features-latest`,
        `:user-<name>-...`) within a single repo; the launcher role's ECR
        resource pattern is `mermaid-*-jobs` to cover both this and the
        segmentation repo. Tagging conventions documented in
        `iac/sagemaker-launcher-convention.md`.
        """
        repo = ecr.Repository(
            self,
            f"{self.prefix}MermaidClassifierJobsRepo",
            repository_name="mermaid-classifier-jobs",
            image_scan_on_push=True,
            removal_policy=cdk.RemovalPolicy.RETAIN,
            lifecycle_rules=[
                ecr.LifecycleRule(
                    description="Keep last 10 images",
                    max_image_count=10,
                    rule_priority=1,
                ),
            ],
        )

        CfnOutput(
            self,
            f"{self.prefix}MermaidClassifierJobsRepoUri",
            value=repo.repository_uri,
            description="ECR URI for the mermaid-classifier jobs image",
            export_name=f"{self.prefix}-MermaidClassifierJobsRepoUri",
        )

        return repo

    def create_segmentation_jobs_repo(self) -> ecr.Repository:
        """ECR repository for the mermaid-segmentation SageMaker job image.

        Sibling of `create_classifier_jobs_repo`. Both repos share
        the `mermaid-*-jobs` naming pattern so the launcher role's ECR
        resource ARN can target them with a single wildcard. Tag-based
        separation (e.g. `:training-latest`, `:processing-latest`,
        `:user-<name>-...`) is documented in the convention doc.
        """
        repo = ecr.Repository(
            self,
            f"{self.prefix}MermaidSegmentationJobsRepo",
            repository_name="mermaid-segmentation-jobs",
            image_scan_on_push=True,
            removal_policy=cdk.RemovalPolicy.RETAIN,
            lifecycle_rules=[
                ecr.LifecycleRule(
                    description="Keep last 10 images",
                    max_image_count=10,
                    rule_priority=1,
                ),
            ],
        )

        CfnOutput(
            self,
            f"{self.prefix}MermaidSegmentationJobsRepoUri",
            value=repo.repository_uri,
            description="ECR URI for the mermaid-segmentation jobs image",
            export_name=f"{self.prefix}-MermaidSegmentationJobsRepoUri",
        )

        return repo

    def create_sagemaker_launcher_role(self) -> iam.Role:
        """IAM role for operators driving the mermaid-* launchers.

        Single shared role used by both mermaid-classifier and
        mermaid-segmentation launcher scripts (training + processing jobs).
        Trust: any principal in this account whose ARN matches the
        SageMaker SSO permission set.

        Permissions: push/pull on the `mermaid-*-jobs` ECR repos, submit and
        observe SageMaker Training+Processing jobs, pass the existing
        SageMaker execution role as the job's RoleArn, read/write the
        run-scoped prefix in the SageMaker data bucket, tail CloudWatch logs.
        """
        sso_principal = iam.PrincipalWithConditions(
            iam.AccountPrincipal(cdk.Aws.ACCOUNT_ID),
            conditions={
                "ArnLike": {
                    "aws:PrincipalArn": (
                        f"arn:aws:iam::{cdk.Aws.ACCOUNT_ID}"
                        ":role/aws-reserved/sso.amazonaws.com"
                        "/AWSReservedSSO_SageMaker_*"
                    ),
                },
            },
        )

        role = iam.Role(
            self,
            f"{self.prefix}MermaidSagemakerLauncherRole",
            assumed_by=sso_principal,
            role_name=f"{self.prefix}-mermaid-sagemaker-launcher-role",
            max_session_duration=cdk.Duration.hours(8),
        )

        # ECR: token + push/pull/manage on mermaid-*-jobs repos in this
        # account. GetAuthorizationToken must be on '*' (AWS rule).
        role.attach_inline_policy(
            iam.Policy(
                self,
                "MermaidSagemakerLauncherEcrPolicy",
                statements=[
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=["ecr:GetAuthorizationToken"],
                        resources=["*"],
                    ),
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=[
                            "ecr:BatchCheckLayerAvailability",
                            "ecr:BatchGetImage",
                            "ecr:GetDownloadUrlForLayer",
                            "ecr:DescribeImages",
                            "ecr:DescribeRepositories",
                            "ecr:ListImages",
                            "ecr:InitiateLayerUpload",
                            "ecr:UploadLayerPart",
                            "ecr:CompleteLayerUpload",
                            "ecr:PutImage",
                            "ecr:BatchDeleteImage",
                        ],
                        resources=[
                            f"arn:aws:ecr:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}"
                            ":repository/mermaid-*-jobs",
                        ],
                    ),
                ],
            )
        )

        # SageMaker: submit + observe both Training and Processing jobs.
        role.attach_inline_policy(
            iam.Policy(
                self,
                "MermaidSagemakerLauncherSagemakerPolicy",
                statements=[
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=[
                            "sagemaker:CreateTrainingJob",
                            "sagemaker:DescribeTrainingJob",
                            "sagemaker:StopTrainingJob",
                            "sagemaker:CreateProcessingJob",
                            "sagemaker:DescribeProcessingJob",
                            "sagemaker:StopProcessingJob",
                            # AddTags/ListTags apply to both job types,
                            # so they're kept on this resource-scoped
                            # statement rather than the unscoped one below.
                            "sagemaker:AddTags",
                            "sagemaker:ListTags",
                        ],
                        resources=[
                            f"arn:aws:sagemaker:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}"
                            ":training-job/*",
                            f"arn:aws:sagemaker:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}"
                            ":processing-job/*",
                        ],
                    ),
                    # List* actions ignore the resource scope but require
                    # the action on '*'. Same for the MLflow presigned-URL
                    # helper if the operator wants to spot-check the UI.
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=[
                            "sagemaker:ListTrainingJobs",
                            "sagemaker:ListProcessingJobs",
                            "sagemaker:ListMlflowApps",
                            "sagemaker:DescribeMlflowApp",
                            "sagemaker:CreatePresignedMlflowAppUrl",
                            "sagemaker-mlflow:*",
                        ],
                        resources=["*"],
                    ),
                ],
            )
        )

        # CloudWatch Logs: tail TrainingJob + ProcessingJob logs from the
        # operator's laptop. The launcher prints CloudWatch URLs at job
        # submission time; `aws logs tail` works from the assumed-role
        # session via these grants. DescribeLogGroups must be on '*' --
        # the CloudWatch API rejects scoped DescribeLogGroups by design.
        role.attach_inline_policy(
            iam.Policy(
                self,
                "MermaidSagemakerLauncherLogsPolicy",
                statements=[
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=["logs:DescribeLogGroups"],
                        resources=["*"],
                    ),
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=[
                            # Read/query actions:
                            "logs:DescribeLogStreams",
                            "logs:GetLogEvents",
                            "logs:FilterLogEvents",
                            # Interactive streaming (separate IAM action):
                            "logs:StartLiveTail",
                        ],
                        # Two-form ARN: the bare log-group ARN covers
                        # the group itself; the `:*` suffix covers its
                        # streams. StartLiveTail/GetLogEvents require
                        # the stream-level form.
                        resources=[
                            f"arn:aws:logs:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}"
                            ":log-group:/aws/sagemaker/*",
                            f"arn:aws:logs:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}"
                            ":log-group:/aws/sagemaker/*:*",
                        ],
                    ),
                ],
            )
        )

        # iam:PassRole on the existing SageMaker execution role -- required
        # to call CreateTraining/ProcessingJob with RoleArn = sm_execution_role.
        role.attach_inline_policy(
            iam.Policy(
                self,
                "MermaidSagemakerLauncherPassRolePolicy",
                statements=[
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=["iam:PassRole"],
                        resources=[self.sm_execution_role.role_arn],
                        conditions={
                            "StringEquals": {"iam:PassedToService": "sagemaker.amazonaws.com"}
                        },
                    ),
                ],
            )
        )

        # S3: launcher syncs the per-run config dir into the data bucket
        # under runs/<run-id>/config/ and reads back log output from
        # runs/<run-id>/output/. Scope tightly to that prefix.
        self.sm_data_bucket.grant_read_write(role, "runs/*")

        CfnOutput(
            self,
            f"{self.prefix}MermaidSagemakerLauncherRoleArn",
            value=role.role_arn,
            description="IAM role for operators driving the mermaid-* launchers",
            export_name=f"{self.prefix}-MermaidSagemakerLauncherRoleArn",
        )

        return role

    def create_sm_sources_bucket(self) -> s3.Bucket:
        return self._create_bucket(
            id=f"{self.prefix}SourcesBucket",
            bucket_name=f"{self.prefix}-datamermaid-sm-sources",
        )

    def create_data_bucket(self) -> s3.Bucket:
        return self._create_bucket(
            id=f"{self.prefix}DataBucket",
            bucket_name=f"{self.prefix}-datamermaid-sm-data",
        )

    def create_ic_datasets_bucket(self) -> s3.Bucket:
        """
        Immutable bucket for versioned image classification datasets (segmentation
        and point classifier).

        The denies cover object-level API calls for every principal, admins
        included: PutObject without If-None-Match under images/, datasets/ and
        taxonomy/, and DeleteObject/DeleteObjectVersion. Bucket configuration
        (the policy itself, lifecycle) is protected by IAM and the CDK
        pipeline, not by these denies. CopyObject into a protected prefix
        must also send If-None-Match: * (403 without it, 412 if the key
        exists); a multipart upload or copy sends it on
        CompleteMultipartUpload.
        """
        bucket = s3.Bucket(
            self,
            id=f"{self.prefix}ICDatasetsBucket",
            bucket_name="mermaid-ic-datasets",
            versioned=True,
            removal_policy=cdk.RemovalPolicy.RETAIN,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            # A crashed publish leaves billed, unlisted parts; the rule never
            # deletes an object or version. Images and masks are read rarely
            # after a cache fill, so they move to Intelligent-Tiering; a
            # transition is not a write or a delete, so the denies allow it.
            lifecycle_rules=[
                s3.LifecycleRule(abort_incomplete_multipart_upload_after=cdk.Duration.days(7)),
                s3.LifecycleRule(
                    prefix="images/",
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INTELLIGENT_TIERING,
                            transition_after=cdk.Duration.days(0),
                        )
                    ],
                ),
            ],
        )

        # The ObjectCreationOperation term exempts the multipart parts, which
        # carry no conditional header.
        bucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="DenyUnconditionalPut",
                effect=iam.Effect.DENY,
                principals=[iam.AnyPrincipal()],
                actions=["s3:PutObject"],
                resources=[
                    bucket.arn_for_objects("images/*"),
                    bucket.arn_for_objects("datasets/*"),
                    bucket.arn_for_objects("taxonomy/*"),
                ],
                conditions={
                    "Null": {"s3:if-none-match": "true"},
                    "Bool": {"s3:ObjectCreationOperation": "true"},
                },
            )
        )
        bucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="DenyObjectDelete",
                effect=iam.Effect.DENY,
                principals=[iam.AnyPrincipal()],
                actions=["s3:DeleteObject", "s3:DeleteObjectVersion"],
                resources=[bucket.arn_for_objects("*")],
            )
        )
        # The denies must outlive the stack.
        assert bucket.policy is not None
        bucket.policy.apply_removal_policy(cdk.RemovalPolicy.RETAIN)
        return bucket

    def _create_bucket(self, id: str, bucket_name: str) -> s3.Bucket:
        return s3.Bucket(
            self,
            id=id,
            bucket_name=bucket_name,
            versioned=False,
            removal_policy=cdk.RemovalPolicy.RETAIN,
            # Access
            access_control=s3.BucketAccessControl.PRIVATE,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            public_read_access=False,
            object_ownership=s3.ObjectOwnership.OBJECT_WRITER,
            enforce_ssl=True,
            # Encryption
            encryption=s3.BucketEncryption.S3_MANAGED,
        )
