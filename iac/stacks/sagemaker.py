import aws_cdk as cdk
from aws_cdk import (
    CfnOutput,
    aws_ec2 as ec2,
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

        # Create IAM role for SageMaker Users
        self.sm_execution_role = self.create_execution_role()

        # Create S3 bucket for SageMaker code sources
        self.sm_sources_bucket = self.create_sm_sources_bucket()

        CfnOutput(
            self,
            f"{self.prefix}SourcesBucketName",
            value=self.sm_sources_bucket.bucket_name,
            description="SageMaker Sources Bucket Name",
            export_name=f"{self.prefix}-SourcesBucketName",
        )

        self.sm_sources_bucket.grant_read_write(self.sm_execution_role)

        # Create S3 bucket for SageMaker data
        self.sm_data_bucket = self.create_data_bucket()

        self.sm_data_bucket.grant_read_write(self.sm_execution_role)

        self.mermaid_image_processing_bucket = s3.Bucket.from_bucket_arn(
            self,
            f"{self.prefix}ImageProcessingBucket",
            bucket_arn="arn:aws:s3:::mermaid-image-processing",
        )

        self.mermaid_image_processing_bucket.grant_read(self.sm_execution_role)

        self.mermaid_config = s3.Bucket.from_bucket_arn(
            self,
            f"{self.prefix}MermaidConfigBucket",
            bucket_arn="arn:aws:s3:::mermaid-config",
        )

        self.mermaid_config.grant_read_write(self.sm_execution_role)

        self.coralnet_public_sources = s3.Bucket.from_bucket_arn(
            self,
            f"{self.prefix}CoralnetPublicSourcesBucket",
            bucket_arn="arn:aws:s3:::2310-coralnet-public-sources",
        )

        self.coralnet_public_sources.grant_read(self.sm_execution_role)

        self.pyspacer_test = s3.Bucket.from_bucket_arn(
            self,
            f"{self.prefix}PyspacerTestBucket",
            bucket_arn="arn:aws:s3:::pyspacer-test",
        )

        self.pyspacer_test.grant_read(self.sm_execution_role)

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
                execution_role=self.sm_execution_role.role_arn,
                security_groups=[
                    self.security_group.security_group_id,
                ],
            ),
            app_network_access_type="VpcOnly",
            vpc_id=self.vpc.vpc_id,
            subnet_ids=private_subnet_ids,
            domain_settings=sm.CfnDomain.DomainSettingsProperty(
                docker_settings=sm.CfnDomain.DockerSettingsProperty(
                    enable_docker_access="ENABLED",
                ),
                security_group_ids=[
                    self.security_group.security_group_id,
                ],
            ),
            default_space_settings=sm.CfnDomain.DefaultSpaceSettingsProperty(
                execution_role=self.sm_execution_role.role_arn,
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
        role = iam.Role(
            self,
            f"{self.prefix}SagemakerExecutionRole",
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
            role_name=f"{self.prefix}-sm-execution-role",
            managed_policies=[
                iam.ManagedPolicy.from_managed_policy_arn(
                    self,
                    id="SagemakerFullAccess",
                    managed_policy_arn="arn:aws:iam::aws:policy/AmazonSageMakerFullAccess",
                ),
                iam.ManagedPolicy.from_managed_policy_arn(
                    self,
                    id="SageMakerStudioFullAccess",
                    managed_policy_arn="arn:aws:iam::aws:policy/SageMakerStudioFullAccess",
                ),
            ],
        )

        role.attach_inline_policy(
            iam.Policy(
                self,
                "MlflowRolePolicy",
                statements=[
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=["sagemaker-mlflow:*"],
                        resources=["*"],
                    )
                ],
            )
        )
        role.attach_inline_policy(
            iam.Policy(
                self,
                "SagemakerStartSessionPolicy",
                statements=[
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=["sagemaker:StartSession"],
                        resources=[
                            f"arn:aws:sagemaker:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:space/*",
                            f"arn:aws:sagemaker:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:user-profile/*",
                            f"arn:aws:sagemaker:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:domain/*",
                        ],
                    )
                ],
            )
        )

        role.attach_inline_policy(
            iam.Policy(
                self,
                "GlueSessionPolicy",
                statements=[
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=[
                            "glue:CreateSession",
                            "glue:GetSession",
                            "glue:DeleteSession",
                            "glue:RunStatement",
                            "glue:GetStatement",
                            "glue:CancelStatement",
                        ],
                        resources=[f"arn:aws:glue:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:session/*"],
                    ),
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=["iam:PassRole"],
                        resources=[role.role_arn],
                        conditions={"StringEquals": {"iam:PassedToService": "glue.amazonaws.com"}},
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

    def _create_bucket(self, id: str, bucket_name: str) -> s3.Bucket:
        return s3.Bucket(
            self,
            id=id,
            bucket_name=bucket_name,
            versioned=True,
            removal_policy=cdk.RemovalPolicy.RETAIN,
            # Access
            access_control=s3.BucketAccessControl.PRIVATE,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            public_read_access=False,
            object_ownership=s3.ObjectOwnership.OBJECT_WRITER,
            enforce_ssl=True,
            # Encryption
            encryption=s3.BucketEncryption.S3_MANAGED,
            # Lifecycle rules
            lifecycle_rules=[
                s3.LifecycleRule(
                    expiration=cdk.Duration.days(90),
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                            transition_after=cdk.Duration.days(30),
                        )
                    ],
                ),
                s3.LifecycleRule(
                    noncurrent_version_expiration=cdk.Duration.days(180),
                    noncurrent_version_transitions=[
                        s3.NoncurrentVersionTransition(
                            storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                            transition_after=cdk.Duration.days(30),
                        )
                    ],
                ),
            ],
        )
