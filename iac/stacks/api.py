from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_rds as rds,
    aws_secretsmanager as secrets,
    aws_s3 as s3,
    aws_elasticloadbalancingv2 as elb
)
from constructs import Construct

from iac.settings import ProjectSettings
from iac.settings.utils import camel_case


class ApiStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        config: ProjectSettings,
        cluster: ecs.Cluster,
        database: rds.DatabaseInstance,
        backup_bucket: s3.Bucket,
        load_balancer: elb.ApplicationLoadBalancer,
        container_security_group: ec2.SecurityGroup,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # namespace = sd.PrivateDnsNamespace(self, "Namespace", name=config.private_dns_name, vpc=self.vpc)

        # svc = "mermaid_api"

        # log_group = logs.LogGroup(
        #     self,
        #     id=f"{id}LogGroup",
        #     log_group_name=f"{config.prefix}-{svc}",
        # )

        task_definition = ecs.FargateTaskDefinition(
            self,
            id="FargateTaskDefinition",
            cpu=config.api.container_cpu,
            memory_limit_mib=config.api.container_memory,
        )

        task_definition.add_container(
            id="MermaidAPI",
            image=ecs.ContainerImage.from_asset(
                directory="../src/", file="Dockerfile"
            ),
            # command=[""], # Need overiding?
            # entry_point=[""], # Need overiding?
            # user="", # Set in Dockerfile?
            port_mappings=[ecs.PortMapping(container_port=80)],
            environment={
                "ENV": f"{config.env_id}",
                "ALLOWED_HOSTS": config.api.allowed_hosts,
                "MAINTENANCE_MODE": config.api.maintenance_mode,
                "ADMINS": config.api.admins,
                "SUPERUSER": config.api.superuser,
                "DEFAULT_DOMAIN_API": config.api.default_domain_api,
                "DEFAULT_DOMAIN_COLLECT": config.api.default_domain_collect,
                "AWS_BACKUP_BUCKET": backup_bucket.bucket_name,
                "EMAIL_HOST": config.api.email_host,
                "EMAIL_PORT": config.api.email_port,
                "EMAIL_HOST_USER": config.api.email_host_user,
                "AUTH0_MANAGEMENT_API_AUDIENCE": config.api.auth0_management_api_audience,
                "MERMAID_API_AUDIENCE": config.api.mermaid_api_audience,
                "MC_USER": config.api.mc_user,
                "CIRCLE_CI_CLIENT_ID": "", # Leave empty

                "DB_NAME": config.database.name,
                "DB_HOST": database.instance_endpoint.hostname
            },
            secrets={
                "DB_USER": ecs.Secret.from_secrets_manager(database.secret, "username"),
                "DB_PASSWORD": ecs.Secret.from_secrets_manager(database.secret, "password"),
                "EMAIL_HOST_PASSWORD": self._get_from_secrets_manager(config.api.email_host_password_name),
                "SECRET_KEY": self._get_from_secrets_manager(config.api.secret_key_name),
                "MERMAID_API_SIGNING_SECRET": self._get_from_secrets_manager(config.api.mermaid_api_signing_secret_name),
                "SPA_ADMIN_CLIENT_ID": self._get_from_secrets_manager(config.api.spa_admin_client_name, key="id"),
                "SPA_ADMIN_CLIENT_SECRET": self._get_from_secrets_manager(config.api.spa_admin_client_name, key="secret"),
                "MERMAID_MANAGEMENT_API_CLIENT_ID": self._get_from_secrets_manager(config.api.mermaid_management_api_client_name, key="id"),
                "MERMAID_MANAGEMENT_API_CLIENT_SECRET": self._get_from_secrets_manager(config.api.mermaid_management_api_client_name, key="secret"),
                "MC_API_KEY": self._get_from_secrets_manager(config.api.mc_api_key_name, key="api_key"),
                "MC_LIST_ID": self._get_from_secrets_manager(config.api.mc_api_key_name, key="list_id"),
            },
            # health_check= # Setup.
        )

        service = ecs.FargateService(
            self,
            id="FargateService",
            task_definition=task_definition,
            platform_version=ecs.FargatePlatformVersion.LATEST,
            cluster=cluster,
            security_groups=[container_security_group],
            # cloud_map_options=ecs.CloudMapOptions(cloud_map_namespace=namespace, name=self.svc),
            desired_count=config.api.container_count,
            enable_execute_command=True,
            vpc_subnets=ec2.SubnetSelection(
                subnets=cluster.vpc.select_subnets(subnet_type=ec2.SubnetType.PRIVATE_WITH_NAT).subnets
            ),
        )

        # add FargateService as target to LoadBalancer/Listener, currently, send all traffic. TODO filter by domain?

        target_group = elb.ApplicationTargetGroup(
            self,
            id="TargetGroup",
            targets=[service],
            protocol=elb.ApplicationProtocol.HTTP,
            vpc=cluster.vpc,
        )

        listener_rule = elb.ApplicationListenerRule(
            self,
            id="ListenerRule",
            listener=load_balancer.listeners[0],
            priority=100,
            # action=elb.ListenerAction.forward(target_groups=[target_group]),
            conditions=[elb.ListenerCondition.path_patterns(values=["/"])],
            # conditions=[elb.ListenerCondition.host_headers([config.api.domain_name])],
            target_groups=[target_group],
        )

        database.connections.allow_from(service.connections, port_range=ec2.Port.tcp(5432))

        backup_bucket.grant_read_write(service.task_definition.task_role)
    
    def _get_from_secrets_manager(self, secret_path: str, key: str = "") -> ecs.Secret:
        """Return secret object from name and field"""
        id = f'{camel_case(secret_path.split("/")[-1])}{key.title()}'
        secret_obj = secrets.Secret.from_secret_name_v2(
            self,
            id=f'SSM-{id}',
            secret_name=secret_path
        )
        if key:
            return ecs.Secret.from_secrets_manager(secret_obj, key)
        else:
            return ecs.Secret.from_secrets_manager(secret_obj)
        
    