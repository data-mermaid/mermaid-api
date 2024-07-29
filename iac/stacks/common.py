import json

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
    aws_autoscaling as autoscale,
    aws_certificatemanager as acm,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_elasticloadbalancingv2 as elb,
    aws_iam as iam,
    aws_kms as kms,
    aws_logs as logs,
    aws_rds as rds,
    aws_route53 as r53,
    aws_s3 as s3,
    aws_secretsmanager as sm,
)
from constructs import Construct


class CommonStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        self.vpc = ec2.Vpc(
            self,
            "Vpc",
            ip_addresses=ec2.IpAddresses.cidr("10.10.0.0/16"),
            max_azs=3,
            nat_gateways=1,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    subnet_type=ec2.SubnetType.PUBLIC,
                    name="Ingress",
                    map_public_ip_on_launch=True,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    name="Application",
                    cidr_mask=20,
                ),
                ec2.SubnetConfiguration(
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    name="Database",
                    cidr_mask=24,
                ),
            ],
        )

        # create s3 gateway endpoint
        self.vpc.add_gateway_endpoint(
            "s3-endpoint",
            service=ec2.GatewayVpcEndpointAwsService.S3,
            subnets=[ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS)],
        )

        # create a SG for the ECR endpoints
        vpc_ep_ecr_sg = ec2.SecurityGroup(
            self,
            id="VPCEndpointsSecurityGroup",
            vpc=self.vpc,
            allow_all_outbound=True,
            description="Security group for VPC Endpoints for ECR",
        )

        # create a secret so we can manually set the username
        database_credentials_secret = sm.Secret(
            self,
            "DBCredentialsSecret",
            secret_name="common/mermaid-db/creds",
            generate_secret_string=sm.SecretStringGenerator(
                secret_string_template=json.dumps({"username": "mermaid_admin"}),
                generate_string_key="password",
                exclude_punctuation=True,
                include_space=False,
            ),
        )

        self.database = rds.DatabaseInstance(
            self,
            "PostgresRdsV2",
            vpc=self.vpc,
            engine=rds.DatabaseInstanceEngine.postgres(version=rds.PostgresEngineVersion.VER_13_7),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE3,
                ec2.InstanceSize.SMALL,
            ),
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            backup_retention=Duration.days(7),
            deletion_protection=True,
            removal_policy=RemovalPolicy.SNAPSHOT,
            credentials=rds.Credentials.from_secret(database_credentials_secret),
        )

        self.backup_bucket = s3.Bucket(
            self,
            id="MermaidApiBackupBucket",
            bucket_name="mermaid-api-v2-backups",
            removal_policy=RemovalPolicy.RETAIN,
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        )

        self.config_bucket = s3.Bucket(
            self,
            id="MermaidApiConfigBucket",
            bucket_name="mermaid-config",
            removal_policy=RemovalPolicy.RETAIN,
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        )

        self.image_processing_bucket = s3.Bucket(
            self,
            id="MermaidImageProcessingBackupBucket",
            bucket_name="mermaid-image-processing",
            removal_policy=RemovalPolicy.RETAIN,
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        )

        # KMS Key for encrypting logs
        ecs_exec_kms_key = kms.Key(self, "ecsExecKmsKey")

        # Pass the KMS key in the `encryptionKey` field to associate the key to the log group
        ecs_exec_log_group = logs.LogGroup(
            self,
            "ECSExecLogGroup",
            encryption_key=ecs_exec_kms_key,
        )

        ecs_exec_config = ecs.ExecuteCommandConfiguration(
            kms_key=ecs_exec_kms_key,
            log_configuration=ecs.ExecuteCommandLogConfiguration(
                cloud_watch_log_group=ecs_exec_log_group,
                cloud_watch_encryption_enabled=True,
            ),
            logging=ecs.ExecuteCommandLogging.OVERRIDE,
        )

        self.fargate_cluster = ecs.Cluster(
            self,
            "MermaidApiCluster",
            vpc=self.vpc,
            container_insights=True,
            enable_fargate_capacity_providers=True,
            execute_command_configuration=ecs_exec_config,
        )

        self.cluster = ecs.Cluster(
            self,
            "EC2MermaidApiCluster",
            vpc=self.vpc,
            container_insights=True,
            enable_fargate_capacity_providers=True,
            execute_command_configuration=ecs_exec_config,
        )

        auto_scaling_group = autoscale.AutoScalingGroup(
            self,
            "ASG",
            vpc=self.vpc,
            instance_type=ec2.InstanceType("t3a.large"),
            machine_image=ecs.EcsOptimizedImage.amazon_linux2(),
            min_capacity=1,
            max_capacity=4,
            # NOTE: not setting the desired capacity so ECS can manage it.
        )

        capacity_provider = ecs.AsgCapacityProvider(
            self,
            "AsgCapacityProvider",
            auto_scaling_group=auto_scaling_group,
            enable_managed_scaling=True,
            enable_managed_termination_protection=False,
        )
        self.cluster.add_asg_capacity_provider(capacity_provider)

        self.cluster.add_default_capacity_provider_strategy(
            [
                ecs.CapacityProviderStrategy(
                    capacity_provider=capacity_provider.capacity_provider_name, weight=100
                )
            ]
        )

        self.load_balancer = elb.ApplicationLoadBalancer(
            self,
            id="MermaidApiLoadBalancer",
            vpc=self.vpc,
            internet_facing=True,
            deletion_protection=True,
        )

        # DNS setup
        root_domain = "datamermaid.org"
        api_domain = f"api2.{root_domain}"

        # lookup hosted zone for the API.
        # NOTE: This depends on the zone already created (manually) and NS's added to cloudflare (manually)
        self.api_zone = r53.HostedZone.from_lookup(
            self,
            "APIZone",
            domain_name=api_domain,
        )

        # SSL Certificates
        # Lookup the cert for *.datamermaid.org
        # NOTE: This depends on the cert already created (manually)
        self.default_cert = acm.Certificate.from_certificate_arn(
            self,
            "DefaultSSLCert",
            certificate_arn=f"arn:aws:acm:us-east-1:{self.account}:certificate/783d7a91-1ebd-4387-9518-e28521086db6",
        )

        self.load_balancer.add_listener(
            id="MermaidApiListener",
            protocol=elb.ApplicationProtocol.HTTPS,
            default_action=elb.ListenerAction.fixed_response(404),
            certificates=[self.default_cert],
        )
        self.load_balancer.add_redirect()

        self.ecs_sg = ec2.SecurityGroup(self, id="EcsSg", vpc=self.vpc, allow_all_outbound=True)

        # Allow ECS tasks to RDS
        self.ecs_sg.connections.allow_to(
            self.database.connections,
            port_range=ec2.Port.tcp(5432),
            description="Allow ECS tasks to RDS",
        )

        # Allow ECS tasks to ECR VPC endpoints
        self.ecs_sg.connections.allow_to(
            vpc_ep_ecr_sg.connections,
            port_range=ec2.Port.tcp(443),
            description="Allow ECS tasks to ECR VPC endpoints",
        )

        create_cdk_bot_user(self, self.account)

        # The following are temporary until prod env is upto date.
        CfnOutput(
            self,
            "ExportsOutputFnGetAttMermaidApiClusterB0854EC6Arn311C07EE",
            value=self.fargate_cluster.cluster_arn,
            export_name="mermaid-api-infra-common:ExportsOutputFnGetAttMermaidApiClusterB0854EC6Arn311C07EE",
        )

        CfnOutput(
            self,
            "ExportsOutputRefMermaidApiClusterB0854EC639332EDF",
            value=self.fargate_cluster.cluster_name,
            export_name="mermaid-api-infra-common:ExportsOutputRefMermaidApiClusterB0854EC639332EDF",
        )


def create_cdk_bot_user(self, account: str):
    cdk_policy = iam.Policy(
        self,
        "CDKRolePolicy",
        statements=[
            iam.PolicyStatement(
                actions=["sts:AssumeRole", "sts:TagSession"],
                effect=iam.Effect.ALLOW,
                resources=[f"arn:aws:iam::{account}:role/cdk-*"],
            )
        ],
    )

    # this user account is used in Github Actions to deploy to AWS
    cicd_bot_user = iam.User(
        self,
        "CICD_Bot",
        user_name="CICD_Bot",
    )
    cicd_bot_user.attach_inline_policy(cdk_policy)