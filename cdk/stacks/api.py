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

from cdk.settings import ProjectSettings


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

        api_secret = secrets.Secret(
            self,
            id="ApiSecret",
            
        )

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
                    directory="../../src/", file="Dockerfile"
                ),
                container_port=80,
                environment={
                    "ENV": f"{config.env_id}",
                    "SECRET_KEY": "", # TODO, move to secrets?
                    "ALLOWED_HOSTS": "", # Comma seperated list
                    "MAINTENANCE_MODE": "False",
                    "MAINTENANCE_MODE_IGNORE_ADMIN_SITE": "True",
                    "MAINTENANCE_MODE_IGNORE_STAFF": "True",
                    "MAINTENANCE_MODE_IGNORE_SUPERUSER": "True",
                    "ADMINS": "", # Comma seperated list
                    "SUPERUSER": "",
                    "DEFAULT_DOMAIN_API": "", # TODO ?
                    "DEFAULT_DOMAIN_COLLECT": "", # TODO ?
                    "AWS_BACKUP_BUCKET": "", # TODO init this bucket as a construct so we can manage permissions.
                    "EMAIL_HOST": "",
                    "EMAIL_PORT": "",
                    "EMAIL_HOST_USER": "",
                    "EMAIL_HOST_PASSWORD": "",
                    "AUTH0_MANAGEMENT_API_AUDIENCE": "",
                    "MERMAID_API_AUDIENCE": "",
                    "MERMAID_API_SIGNING_SECRET": "", # TODO secret?
                    "SPA_ADMIN_CLIENT_ID": "", # TODO secret?
                    "SPA_ADMIN_CLIENT_SECRET": "", # TODO secret?
                    "MERMAID_MANAGEMENT_API_CLIENT_ID": "", # TODO secret?
                    "MERMAID_MANAGEMENT_API_CLIENT_SECRET": "", # TODO secret?
                    "CIRCLE_CI_CLIENT_ID": "",
                    "MC_API_KEY": "", # TODO secret?
                    "MC_USER": "",
                    "MC_LIST_ID": "",

                    "DB_NAME": config.database.name,
                    "DB_HOST": database.instance_endpoint.hostname
                },
                secrets={
                    "DB_USER": ecs.Secret.from_secrets_manager(database.secret, "username"),
                    "DB_PASSWORD": ecs.Secret.from_secrets_manager(database.secret, "password"),
                },
                enable_logging=True,
                # log_driver=ecs.LogDrivers.aws_logs(
                #     stream_prefix=svc, log_group=log_group
                # ),
            ),
        )

        self.service = stac_fastapi.service