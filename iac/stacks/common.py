import json

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
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
            cidr="10.10.0.0/16",
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

        # create VPC endopoints for ECR
        self.vpc.add_interface_endpoint(
            "ecr-api-endpoint",
            service=ec2.InterfaceVpcEndpointAwsService.ECR,
            subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            security_groups=[vpc_ep_ecr_sg],
        )
        self.vpc.add_interface_endpoint(
            "ecr-dkr-endpoint",
            service=ec2.InterfaceVpcEndpointAwsService.ECR_DOCKER,
            subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            security_groups=[vpc_ep_ecr_sg],
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

        # KMS Key for encrypting logs
        ecs_exec_kms_key = kms.Key(self, "ecsExecKmsKey")
        ecs_exec_kms_key.add_to_resource_policy(
            statement=iam.PolicyStatement(
                actions=["kms:Encrypt*", "kms:Decrypt*", "kms:ReEncrypt*", "kms:GenerateDataKey*", "kms:Describe*"],
                resources=["*"],
                principals=[iam.ServicePrincipal("logs.us-east-1.amazonaws.com")],
                effect=iam.Effect.ALLOW,
                conditions={
                    "ArnLike":{
                        "kms:EncryptionContext:aws:logs:arn":{
                            "Fn::Join": [
                                "",
                                [
                                    "arn:",
                                    {"Ref": "AWS::Partition"},
                                    ":logs:us-east-1:554812291621:*"
                                ],
                            ],
                        },
                    },
                },
            )
        )

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
            "MermaidApiCluster",
            vpc=self.vpc,
            container_insights=True,
            enable_fargate_capacity_providers=True,
            execute_command_configuration=ecs_exec_config,
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

        self.ecs_sg.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            # ec2.Peer.security_group_id(self.load_balancer.load_balancer_security_groups[0]),
            ec2.Port.tcp(8081),
        )

        self.ecs_sg.add_egress_rule(
            ec2.Peer.any_ipv4(),
            # ec2.Peer.security_group_id(self.load_balancer.load_balancer_security_groups[0]),
            ec2.Port.tcp(8081),
        )

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

        CfnOutput(
            self,
            "ExportsOutputRefVpc8378EB38272D6E3A",
            value=self.vpc.vpc_id,
            export_name="mermaid-api-infra-common:ExportsOutputRefVpc8378EB38272D6E3A",
        )

        CfnOutput(
            self,
            "ExportsOutputFnGetAttecsExecKmsKey22C03821Arn262DB0C8",
            value=ecs_exec_kms_key.key_arn,
            export_name="mermaid-api-infra-common:ExportsOutputFnGetAttecsExecKmsKey22C03821Arn262DB0C8"
        )

        CfnOutput(
            self,
            "ExportsOutputRefECSExecLogGroup95B1C6C87E932D48",
            value= ecs_exec_log_group.log_group_name,
            export_name="mermaid-api-infra-common:ExportsOutputRefECSExecLogGroup95B1C6C87E932D48"
        )

        CfnOutput(
            self,
            "ExportsOutputFnGetAttMermaidApiBackupBucket3C31FBC2ArnD4FB466E",
            value=self.backup_bucket.bucket_arn,
            export_name="mermaid-api-infra-common:ExportsOutputFnGetAttMermaidApiBackupBucket3C31FBC2ArnD4FB466E"
        )

        CfnOutput(
            self,
            "ExportsOutputFnGetAttMermaidApiLoadBalancer302DB6A0DNSNameB6018BD2",
            value=self.load_balancer.load_balancer_dns_name,
            export_name="mermaid-api-infra-common:ExportsOutputFnGetAttMermaidApiLoadBalancer302DB6A0DNSNameB6018BD2"
        )

        CfnOutput(
            self,
            "ExportsOutputRefMermaidApiBackupBucket3C31FBC24D4BC6E3",
            value=self.backup_bucket.bucket_name,
            export_name="mermaid-api-infra-common:ExportsOutputRefMermaidApiBackupBucket3C31FBC24D4BC6E3"
        )

        CfnOutput(
            self,
            "ExportsOutputFnGetAttPostgresRdsV2B4B63A33EndpointAddressA3E1344A",
            value=self.database.db_instance_endpoint_address,
            export_name="mermaid-api-infra-common:ExportsOutputFnGetAttPostgresRdsV2B4B63A33EndpointAddressA3E1344A"
        )

        CfnOutput(
            self,
            "ExportsOutputRefDBCredentialsSecretAttachment8D28662CBA0EF0C2",
            value=self.database.as_secret_attachment_target().target_id,
            export_name="mermaid-api-infra-common:ExportsOutputRefDBCredentialsSecretAttachment8D28662CBA0EF0C2"
        )

        CfnOutput(
            self,
            "ExportsOutputFnGetAttMermaidApiClusterB0854EC6Arn311C07EE",
            value=self.cluster.cluster_arn,
            export_name="mermaid-api-infra-common:ExportsOutputFnGetAttMermaidApiClusterB0854EC6Arn311C07EE"
        )


        CfnOutput(
            self,
            "ExportsOutputRefVpcApplicationSubnet1SubnetDBACD68002B54A62",
            value=self.vpc.select_subnets(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS).subnets[0].subnet_id,
            export_name="mermaid-api-infra-common:ExportsOutputRefVpcApplicationSubnet1SubnetDBACD68002B54A62"
        )

        CfnOutput(
            self,
            "ExportsOutputRefVpcApplicationSubnet2Subnet171884C2D73013E3",
            value=self.vpc.select_subnets(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS).subnets[1].subnet_id,
            export_name="mermaid-api-infra-common:ExportsOutputRefVpcApplicationSubnet2Subnet171884C2D73013E3"
        )

        CfnOutput(
            self,
            "ExportsOutputRefVpcApplicationSubnet3SubnetCDBFDB035B675484",
            value=self.vpc.select_subnets(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS).subnets[2].subnet_id,
            export_name="mermaid-api-infra-common:ExportsOutputRefVpcApplicationSubnet3SubnetCDBFDB035B675484"
        )

        CfnOutput(
            self,
            "ExportsOutputFnGetAttEcsSg17B4B0B3GroupIdF7EB5B8E",
            value=self.ecs_sg.security_group_id,
            export_name="mermaid-api-infra-common:ExportsOutputFnGetAttEcsSg17B4B0B3GroupIdF7EB5B8E"
        )

        CfnOutput(
            self,
            "ExportsOutputRefMermaidApiClusterB0854EC639332EDF",
            value=self.cluster.cluster_name,
            export_name="mermaid-api-infra-common:ExportsOutputRefMermaidApiClusterB0854EC639332EDF"
        )

        CfnOutput(
            self,
            "ExportsOutputFnGetAttMermaidApiLoadBalancer302DB6A0CanonicalHostedZoneIDC5DCD9C8",
            value=self.load_balancer.load_balancer_canonical_hosted_zone_id,
            export_name="mermaid-api-infra-common:ExportsOutputFnGetAttMermaidApiLoadBalancer302DB6A0CanonicalHostedZoneIDC5DCD9C8"
        )

        CfnOutput(
            self,
            "ExportsOutputRefMermaidApiLoadBalancerMermaidApiListenerA1568DCDCCBFF169",
            value=self.load_balancer.listeners[0].listener_arn,
            export_name="mermaid-api-infra-common:ExportsOutputRefMermaidApiLoadBalancerMermaidApiListenerA1568DCDCCBFF169"
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
