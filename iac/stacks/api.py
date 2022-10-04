import os
from importlib import resources
from aws_cdk import (
    Stack,
    Duration,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_applicationautoscaling as appscaling,
    aws_ecr_assets as ecr_assets,
    aws_rds as rds,
    aws_s3 as s3,
    aws_elasticloadbalancingv2 as elb,
    aws_logs as logs,
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

        task_definition = ecs.FargateTaskDefinition(
            self,
            id="FargateTaskDefinition",
            cpu=config.api.container_cpu,
            memory_limit_mib=config.api.container_memory,
        )

        # Secrets
        api_secrets = {
            "DB_USER": ecs.Secret.from_secrets_manager(database.secret, "username"),
            "DB_PASSWORD": ecs.Secret.from_secrets_manager(database.secret, "password"),
            "PGPASSWORD": ecs.Secret.from_secrets_manager(database.secret, "password"),
            "DRF_RECAPTCHA_SECRET_KEY": ecs.Secret.from_secrets_manager(config.api.get_secret_object(self, config.api.drf_recaptcha_secret_key_name)),
            "EMAIL_HOST_USER": ecs.Secret.from_secrets_manager(
                config.api.get_secret_object(self, config.api.email_host_user_name)
            ),
            "EMAIL_HOST_PASSWORD": ecs.Secret.from_secrets_manager(
                config.api.get_secret_object(self, config.api.email_host_password_name)
            ),
            "SECRET_KEY": ecs.Secret.from_secrets_manager(
                config.api.get_secret_object(self, config.api.secret_key_name)
            ),
            "MERMAID_API_SIGNING_SECRET": ecs.Secret.from_secrets_manager(
                config.api.get_secret_object(
                    self, config.api.mermaid_api_signing_secret_name
                )
            ),
            "SPA_ADMIN_CLIENT_ID": ecs.Secret.from_secrets_manager(
                config.api.get_secret_object(self, config.api.spa_admin_client_id_name)
            ),
            "SPA_ADMIN_CLIENT_SECRET": ecs.Secret.from_secrets_manager(
                config.api.get_secret_object(
                    self, config.api.spa_admin_client_secret_name
                )
            ),
            "MERMAID_MANAGEMENT_API_CLIENT_ID": ecs.Secret.from_secrets_manager(
                config.api.get_secret_object(
                    self, config.api.mermaid_management_api_client_id_name
                )
            ),
            "MERMAID_MANAGEMENT_API_CLIENT_SECRET": ecs.Secret.from_secrets_manager(
                config.api.get_secret_object(
                    self, config.api.mermaid_management_api_client_secret_name
                )
            ),
            "MC_API_KEY": ecs.Secret.from_secrets_manager(
                config.api.get_secret_object(self, config.api.mc_api_key_name)
            ),
            "MC_LIST_ID": ecs.Secret.from_secrets_manager(
                config.api.get_secret_object(self, config.api.mc_api_list_id_name)
            ),
            "ADMINS": ecs.Secret.from_secrets_manager(
                config.api.get_secret_object(self, config.api.admins_name)
            ),
            "SUPERUSER": ecs.Secret.from_secrets_manager(
                config.api.get_secret_object(self, config.api.superuser_name)
            ),
        }

        if config.env_id == "dev":
            api_secrets["DEV_EMAILS"] = ecs.Secret.from_secrets_manager(
                config.api.get_secret_object(self, config.api.dev_emails_name)
            )

        # Envir Vars
        environment={
            "ENV": config.env_id,
            "ENVIRONMENT": config.env_id,
            "ALLOWED_HOSTS": load_balancer.load_balancer_dns_name,
            "MAINTENANCE_MODE": config.api.maintenance_mode,
            "DEFAULT_DOMAIN_API": config.api.default_domain_api,
            "DEFAULT_DOMAIN_COLLECT": config.api.default_domain_collect,
            "AWS_BACKUP_BUCKET": backup_bucket.bucket_name,
            "EMAIL_HOST": config.api.email_host,
            "EMAIL_PORT": config.api.email_port,
            "AUTH0_MANAGEMENT_API_AUDIENCE": config.api.auth0_management_api_audience,
            "MERMAID_API_AUDIENCE": config.api.mermaid_api_audience,
            "MC_USER": config.api.mc_user,
            "CIRCLE_CI_CLIENT_ID": "",  # Leave empty
            "DB_NAME": config.database.name,
            "DB_HOST": database.instance_endpoint.hostname,
            "DB_PORT": config.database.port,
        }

        # build image asset to be shared with API and Backup Task
        image_asset = ecr_assets.DockerImageAsset(
            self,
            "ApiImage",
            directory="../", 
            file="Dockerfile.ecs",
        )

        # create a scheduled fargate task
        backup_task = ecs_patterns.ScheduledFargateTask(
            self,
            "ScheduledBackupTask",
            # schedule=appscaling.Schedule.rate(Duration.days(1)),
            schedule=appscaling.Schedule.cron(hour="23"),
            cluster=cluster,
            security_groups=[container_security_group],
            scheduled_fargate_task_image_options=ecs_patterns.ScheduledFargateTaskImageOptions(
                image=ecs.ContainerImage.from_docker_image_asset(image_asset),
                cpu=config.api.container_cpu,
                memory_limit_mib=config.api.container_memory,
                secrets=api_secrets,
                environment=environment,
                command=[f"python manage.py dbbackup {config.env_id}"]
            ),
        )

        task_definition.add_container(
            id="MermaidAPI",
            image=ecs.ContainerImage.from_docker_image_asset(image_asset),
            port_mappings=[ecs.PortMapping(container_port=8081)],
            environment=environment,
            secrets=api_secrets,
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix=config.env_id, log_retention=logs.RetentionDays.ONE_MONTH
            ),
            # health_check=elb.HealthCheck(
            #     command=["CMD-SHELL", "curl --fail http://localhost:80/v1/health/ || exit 1"],
            #     interval=Duration.seconds(60),
            #     retries=5,
            #     timeout=Duration.seconds(10),
            #     start_period=Duration.seconds(20),
            # )
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
                subnets=cluster.vpc.select_subnets(
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_NAT
                ).subnets
            ),
            # capacity_provider_strategies=ecs.CapacityProviderStrategy(
            #     capacity_provider="FARGATE_SPOT",
            #     base=1,
            #     weight=50 # Not sure about this.
            # ) # Manually set FARGATE_SPOT as deafult in cluster console.
        )


        # Grant Secret read to API container
        for _, container_secret in api_secrets.items():
            container_secret.grant_read(service.task_definition.execution_role)
            container_secret.grant_read(backup_task.task_definition.execution_role)

        # add FargateService as target to LoadBalancer/Listener, currently, send all traffic. TODO filter by domain?

        target_group = elb.ApplicationTargetGroup(
            self,
            id="TargetGroup",
            targets=[service],
            protocol=elb.ApplicationProtocol.HTTP,
            vpc=cluster.vpc,
            health_check=elb.HealthCheck(
                path="/health/",
                healthy_http_codes="200",
                healthy_threshold_count=4,
                unhealthy_threshold_count=4,
                timeout=Duration.seconds(10),
                interval=Duration.seconds(60),
                port="8081",
            ),
        )

        listener_rule = elb.ApplicationListenerRule(
            self,
            id="ListenerRule",
            listener=load_balancer.listeners[0],
            priority=100,
            # action=elb.ListenerAction.forward(target_groups=[target_group]),
            conditions=[elb.ListenerCondition.path_patterns(values=["/*"])],
            # conditions=[elb.ListenerCondition.host_headers([config.api.domain_name])],
            target_groups=[target_group],
        )

        # Is this required? We has a custom SG already defined...
        database.connections.allow_from(
            service.connections, port_range=ec2.Port.tcp(5432)
        )

        backup_bucket.grant_read_write(service.task_definition.task_role)
        backup_bucket.grant_read_write(backup_task.task_definition.execution_role)
