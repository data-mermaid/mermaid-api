from turtle import title
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_rds as rds,
    aws_servicediscovery as sd,
    aws_secretsmanager as secrets,
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
        vpc: ec2.Vpc,
        database: rds.DatabaseInstance,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        cluster = ecs.Cluster(self, "Cluster", vpc=vpc, container_insights=True)

        # namespace = sd.PrivateDnsNamespace(self, "Namespace", name=config.private_dns_name, vpc=self.vpc)

        # svc = "mermaid_api"

        # log_group = logs.LogGroup(
        #     self,
        #     id=f"{id}LogGroup",
        #     log_group_name=f"{config.prefix}-{svc}",
        # )

        mermaid_api = ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            id="MermaidApi",
            cluster=cluster,
            cpu=config.api.container_cpu,
            memory_limit_mib=config.api.container_memory,
            desired_count=config.api.container_count,
            # protocol=elb.ApplicationProtocol.HTTPS,
            # domain_zone=r53.HostedZone.from_lookup(
            #     self, id=f"{config.prefix}-hosted-zone", domain_name=config.domain_name
            # ),
            # domain_name=config.stacfastapi.domain_name,
            # redirect_http=True,
            # cloud_map_options=ecs.CloudMapOptions(
            #     cloud_map_namespace=namespace, name=svc
            # ),
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_asset(
                    directory="../src/", file="Dockerfile"
                ),
                container_port=80,
                environment={
                    "ENV": f"{config.env_id}",
                    "ALLOWED_HOSTS": config.api.allowed_hosts,
                    "MAINTENANCE_MODE": config.api.maintenance_mode,
                    "ADMINS": config.api.admins,
                    "SUPERUSER": config.api.superuser,
                    "DEFAULT_DOMAIN_API": config.api.default_domain_api,
                    "DEFAULT_DOMAIN_COLLECT": config.api.default_domain_collect,
                    "AWS_BACKUP_BUCKET": "", # TODO init this bucket as a construct so we can manage permissions.
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
                enable_logging=True,
                # log_driver=ecs.LogDrivers.aws_logs(
                #     stream_prefix=svc, log_group=log_group
                # ),
            ),
        )

        self.service = mermaid_api.service
    
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
        
    