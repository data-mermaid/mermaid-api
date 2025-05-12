import aws_cdk as cdk
from aws_cdk import (
    aws_sagemaker as sm,
    aws_iam as iam,
    aws_s3 as s3,
    aws_ssm as ssm,
    aws_ecs as ecs,
)
from constructs import Construct
from settings.settings import ProjectSettings


class SagemakerStack(cdk.Stack):
    def __init__(
        self, scope: Construct, id: str, config: ProjectSettings, cluster: ecs.Cluster, **kwargs
    ) -> None:
        super().__init__(scope, id, **kwargs)

        self.prefix = config.env_id

        # Create IAM role for SageMaker Users
        self.sm_execution_role = self.create_execution_role()

        # Create S3 bucket for SageMaker code sources
        self.sm_sources_bucket = self.create_sm_sources_bucket()

        ssm.StringParameter(
            self,
            f"{self.prefix}SourcesBucketName",
            string_value=self.sm_sources_bucket.bucket_name,
            parameter_name=f"/{self.prefix}/SourcesBucketName",
            description="SageMaker Sources Bucket Name",
        )

        # Grant read access to SageMaker execution role
        self.sm_sources_bucket.grant_read(self.sm_execution_role)

        # Create S3 bucket for SageMaker data
        self.sm_data_bucket = self.create_data_bucket()

        # Grant read/write access to SageMaker execution role
        self.sm_data_bucket.grant_read_write(self.sm_execution_role)

        # Fetch VPC information
        self.vpc = cluster.vpc
        public_subnet_ids = [public_subnet.subnet_id for public_subnet in self.vpc.public_subnets]

        # Create SageMaker Studio domain
        self.domain = sm.CfnDomain(
            self,
            f"{self.prefix}SagemakerDomain",
            auth_mode="IAM",
            domain_name=f"{self.prefix}-SG-Project",
            default_user_settings=sm.CfnDomain.UserSettingsProperty(
                execution_role=self.sm_execution_role.role_arn
            ),
            app_network_access_type="PublicInternetOnly",
            vpc_id=self.vpc.vpc_id,
            subnet_ids=public_subnet_ids,
            tags=[cdk.CfnTag(key="project", value="example-pipelines")],
        )

        # Create SageMaker Studio default user profile
        self.user = sm.CfnUserProfile(
            self,
            f"{self.prefix}SageMakerStudioUserProfile",
            domain_id=self.domain.attr_domain_id,
            user_profile_name="default-user",
            user_settings=sm.CfnUserProfile.UserSettingsProperty(),
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
            ],
        )
        ssm.StringParameter(
            self,
            f"{self.prefix}SagemakerExecutionRoleArn",
            string_value=role.role_arn,
            parameter_name=f"/{self.prefix}/SagemakerExecutionRoleArn",
            description="SageMaker Execution Role ARN",
        )

        return role

    def create_sm_sources_bucket(self) -> s3.Bucket:
        return s3.Bucket(
            self,
            id=f"{self.prefix}SourcesBucket",
            bucket_name=f"{self.prefix}-sm-sources",
            lifecycle_rules=[],
            versioned=False,
            removal_policy=cdk.RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            # Access
            access_control=s3.BucketAccessControl.PRIVATE,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            public_read_access=False,
            object_ownership=s3.ObjectOwnership.OBJECT_WRITER,
            enforce_ssl=True,
            # Encryption
            encryption=s3.BucketEncryption.S3_MANAGED,
        )

    def create_data_bucket(self) -> s3.Bucket:
        return s3.Bucket(
            self,
            id=f"{self.prefix}DataBucket",
            bucket_name=f"{self.prefix}-sm-data",
            lifecycle_rules=[],
            versioned=False,
            removal_policy=cdk.RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            # Access
            access_control=s3.BucketAccessControl.PRIVATE,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            public_read_access=False,
            object_ownership=s3.ObjectOwnership.OBJECT_WRITER,
            enforce_ssl=True,
            # Encryption
            encryption=s3.BucketEncryption.S3_MANAGED,
        )
