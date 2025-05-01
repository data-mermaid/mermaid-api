import json

from aws_cdk import (
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
    def _database(self, id: str, version: rds.PostgresEngineVersion) -> rds.DatabaseInstance:
        # create a secret so we can manually set the username
        database_credentials_secret = sm.Secret(
            self,
            f"{id}Secret",
            secret_name=f"common/mermaid-db/creds-{id}",
            generate_secret_string=sm.SecretStringGenerator(
                secret_string_template=json.dumps({"username": "mermaid_admin"}),
                generate_string_key="password",
                exclude_punctuation=True,
                include_space=False,
            ),
        )

        return rds.DatabaseInstance(
            self,
            id,
            vpc=self.vpc,
            engine=rds.DatabaseInstanceEngine.postgres(version=version),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE3,
                ec2.InstanceSize.MEDIUM,
            ),
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            backup_retention=Duration.days(7),
            deletion_protection=True,
            removal_policy=RemovalPolicy.SNAPSHOT,
            credentials=rds.Credentials.from_secret(database_credentials_secret),
        )

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

        self.dev_database = self._database(
            id="PostgresRdsV2Dev", version=rds.PostgresEngineVersion.VER_16_3
        )

        self.prod_database = self._database(
            id="PostgresRdsV2", version=rds.PostgresEngineVersion.VER_13_7
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

        self.data_bucket = s3.Bucket(
            self,
            id="MermaidApiDataBucket",
            bucket_name="mermaid-data",
            removal_policy=RemovalPolicy.RETAIN,
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            lifecycle_rules=[
                # Rules for cleaning up report files after 14 days.
                s3.LifecycleRule(
                    id="LocalReportsLifecycle",
                    prefix="local/reports/",
                    expiration=Duration.days(14),
                ),
                s3.LifecycleRule(
                    id="DevReportsLifecycle", prefix="dev/reports/", expiration=Duration.days(14)
                ),
                s3.LifecycleRule(
                    id="ProdReportsLifecycle", prefix="prod/reports/", expiration=Duration.days(14)
                ),
            ],
        )

        self.image_processing_bucket = s3.Bucket(
            self,
            id="MermaidImageProcessingBackupBucket",
            bucket_name="mermaid-image-processing",
            removal_policy=RemovalPolicy.RETAIN,
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            cors=[
                s3.CorsRule(
                    allowed_methods=[
                        s3.HttpMethods.GET,
                        s3.HttpMethods.HEAD,
                    ],
                    allowed_origins=["*"],
                    allowed_headers=["*"],
                    exposed_headers=[],
                    max_age=3000,
                ),
            ],
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

        self.cluster = ecs.Cluster(
            self,
            "EC2MermaidApiCluster",
            vpc=self.vpc,
            container_insights=True,
            enable_fargate_capacity_providers=True,
            execute_command_configuration=ecs_exec_config,
        )

        self.ecs_sg = ec2.SecurityGroup(self, id="EcsSg", vpc=self.vpc, allow_all_outbound=True)

        # Allow ECS tasks to RDS
        self.dev_database.connections.allow_default_port_from(self.ecs_sg)
        self.prod_database.connections.allow_default_port_from(self.ecs_sg)

        # FIX - add each subnet CIDR block.
        selection = self.vpc.select_subnets(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS)
        for subnet in selection.subnets:
            self.dev_database.connections.allow_default_port_from(
                ec2.Peer.ipv4(subnet.ipv4_cidr_block)
            )
            self.prod_database.connections.allow_default_port_from(
                ec2.Peer.ipv4(subnet.ipv4_cidr_block)
            )

        user_data = ec2.UserData.for_linux()
        user_data.add_commands(
            "yum update --security",
        )

        auto_scaling_group_lt = autoscale.AutoScalingGroup(
            self,
            "ASG2",
            vpc=self.vpc,
            launch_template=ec2.LaunchTemplate(
                self,
                "LTemp",
                instance_type=ec2.InstanceType("t3a.large"),
                machine_image=ecs.EcsOptimizedImage.amazon_linux2(),
                block_devices=[
                    ec2.BlockDevice(
                        device_name="/dev/xvda",
                        volume=ec2.BlockDeviceVolume.ebs(100),
                    ),
                ],
                user_data=user_data,
                security_group=self.ecs_sg,
                role=iam.Role(
                    self, "AsgInstance", assumed_by=iam.ServicePrincipal("ec2.amazonaws.com")
                ),
            ),
            min_capacity=1,
            max_capacity=10,
            max_instance_lifetime=Duration.days(7),
            update_policy=autoscale.UpdatePolicy.rolling_update(),
            # NOTE: not setting the desired capacity so ECS can manage it.
        )

        capacity_provider_lt = ecs.AsgCapacityProvider(
            self,
            "AsgCapacityProviderLt",
            auto_scaling_group=auto_scaling_group_lt,
            enable_managed_scaling=True,
            enable_managed_termination_protection=False,
        )
        self.cluster.add_asg_capacity_provider(capacity_provider_lt)

        self.cluster.add_default_capacity_provider_strategy(
            [
                ecs.CapacityProviderStrategy(
                    capacity_provider=capacity_provider_lt.capacity_provider_name, weight=100
                ),
            ]
        )

        self.load_balancer = elb.ApplicationLoadBalancer(
            self,
            id="MermaidApiLoadBalancer",
            vpc=self.vpc,
            internet_facing=True,
            deletion_protection=True,
            idle_timeout=Duration.seconds(300),  # To match webserver timeout
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

        create_cdk_bot_user(self, self.account)


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
