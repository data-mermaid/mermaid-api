from aws_cdk import (
    Duration,
    RemovalPolicy,
    Stack,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_s3 as s3,
    aws_ecs as ecs,
    aws_elasticloadbalancingv2 as elb
)
from constructs import Construct

from iac.settings import ProjectSettings


class CommonStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        config: ProjectSettings,
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
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_NAT,
                    name="Application",
                    cidr_mask=20,
                ),
                ec2.SubnetConfiguration(
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    name="Database",
                    cidr_mask=24,
                ),
            ]
        )

        self.database = rds.DatabaseInstance(
            self,
            "PostgresRds",
            vpc=self.vpc,
            engine=rds.DatabaseInstanceEngine.POSTGRES,
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.MICRO),
            # database_name=config.database.name,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            backup_retention=Duration.days(7),
            deletion_protection=True,
            removal_policy=RemovalPolicy.SNAPSHOT,
        )

        bastion = ec2.BastionHostLinux(
            self,
            "Bastion",
            vpc=self.vpc,
            subnet_selection=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            init=ec2.CloudFormationInit.from_elements(
                ec2.InitPackage.yum("postgresql"),
                ec2.InitPackage.yum("postgresql-devel")
            ),
            # init_options=ec2.ApplyCloudFormationInitOptions(),
        )
        # Allow from EC2_INSTANCE_CONNECT: 
        # https://docs.aws.amazon.com/general/latest/gr/aws-ip-ranges.html#aws-ip-download
        # jq -r '.prefixes[] | select(.region=="us-east-1") | select(.service=="EC2_INSTANCE_CONNECT") | .ip_prefix' < ~/.aws/ip-ranges.json
        # 18.206.107.24/29
        bastion.allow_ssh_access_from(ec2.Peer.ipv4("18.206.107.24/29"))

        self.database.connections.allow_from(bastion.connections, port_range=ec2.Port.tcp(5432))

        self.backup_bucket = s3.Bucket(
            self,
            id="MermaidApiBackupBucket",
            bucket_name=config.backup_bucket_name,
            removal_policy=RemovalPolicy.RETAIN,
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        )

        self.cluster = ecs.Cluster(
            self, 
            "MermaidApiCluster", 
            vpc=self.vpc, 
            container_insights=True,
            enable_fargate_capacity_providers=True,
        )

        self.load_balancer = elb.ApplicationLoadBalancer(
            self,
            id="MermaidApiLoadBalancer",
            vpc=self.vpc,
            internet_facing=True,
        )

        self.load_balancer.add_listener(
            id="MermaidApiListener",
            port=80, # Until a domain is sorted out
            protocol=elb.ApplicationProtocol.HTTP,
            default_action=elb.ListenerAction.fixed_response(404)
        )
        # self.load_balancer.add_redirect() # Needs to be HTTPs first.

        alb_sg = ec2.SecurityGroup(
            self, 
            id="AlbSg", 
            vpc=self.vpc, 
            allow_all_outbound=True
        )
        alb_sg.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(), 
            connection=ec2.Port.tcp(443), 
            description="Allow incoming https traffic"
        )

        self.ecs_sg = ec2.SecurityGroup(
            self, 
            id="EcsSg", 
            vpc=self.vpc, 
            allow_all_outbound=True
        )
        self.ecs_sg.connections.allow_from(
            other=alb_sg, 
            port_range=ec2.Port.all_tcp(), 
            description="Application load balancer"
        )

        self.load_balancer.add_security_group(alb_sg)
