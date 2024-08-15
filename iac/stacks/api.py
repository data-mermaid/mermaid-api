import os

from aws_cdk import (
    Duration,
    Stack,
    aws_applicationautoscaling as appscaling,
    aws_ec2 as ec2,
    aws_ecr_assets as ecr_assets,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_elasticloadbalancingv2 as elb,
    aws_logs as logs,
    aws_rds as rds,
    aws_route53 as r53,
    aws_route53_targets as r53_targets,
    aws_s3 as s3,
)
from constructs import Construct
from settings import ProjectSettings
from stacks.constructs.worker import QueueWorker


class ApiStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        config: ProjectSettings,
        cluster: ecs.Cluster,
        database: rds.DatabaseInstance,
        backup_bucket: s3.Bucket,
        config_bucket: s3.Bucket,
        public_bucket: s3.Bucket,
        load_balancer: elb.ApplicationLoadBalancer,
        container_security_group: ec2.SecurityGroup,
        api_zone: r53.HostedZone,
        image_processing_bucket: s3.Bucket,
        use_fifo_queues: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        task_definition = ecs.Ec2TaskDefinition(
            self, id="ApiTaskDefinition", network_mode=ecs.NetworkMode.AWS_VPC
        )

        sys_email = os.environ.get("SYS_EMAIL") or None

        # Secrets
        api_secrets = {
            "DB_USER": ecs.Secret.from_secrets_manager(database.secret, "username"),
            "DB_PASSWORD": ecs.Secret.from_secrets_manager(database.secret, "password"),
            "PGPASSWORD": ecs.Secret.from_secrets_manager(database.secret, "password"),
            "DRF_RECAPTCHA_SECRET_KEY": ecs.Secret.from_secrets_manager(
                config.api.get_secret_object(self, config.api.drf_recaptcha_secret_key_name)
            ),
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
                config.api.get_secret_object(self, config.api.mermaid_api_signing_secret_name)
            ),
            "SPA_ADMIN_CLIENT_ID": ecs.Secret.from_secrets_manager(
                config.api.get_secret_object(self, config.api.spa_admin_client_id_name)
            ),
            "SPA_ADMIN_CLIENT_SECRET": ecs.Secret.from_secrets_manager(
                config.api.get_secret_object(self, config.api.spa_admin_client_secret_name)
            ),
            "MERMAID_MANAGEMENT_API_CLIENT_ID": ecs.Secret.from_secrets_manager(
                config.api.get_secret_object(self, config.api.mermaid_management_api_client_id_name)
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
            "AUTH0_DOMAIN": ecs.Secret.from_secrets_manager(
                config.api.get_secret_object(self, config.api.auth0_domain)
            ),
        }

        if config.env_id == "dev":
            api_secrets["DEV_EMAILS"] = ecs.Secret.from_secrets_manager(
                config.api.get_secret_object(self, config.api.dev_emails_name)
            )

        # Envir Vars
        sqs_queue_name = f"mermaid-{config.env_id}-queue"
        image_sqs_queue_name = f"mermaid-{config.env_id}-image-processing-queue"
        environment = {
            "ENV": config.env_id,
            "ENVIRONMENT": config.env_id,
            "ALLOWED_HOSTS": load_balancer.load_balancer_dns_name,
            "MAINTENANCE_MODE": config.api.maintenance_mode,
            "DEFAULT_DOMAIN_API": config.api.default_domain_api,
            "DEFAULT_DOMAIN_COLLECT": config.api.default_domain_collect,
            "AWS_BACKUP_BUCKET": backup_bucket.bucket_name,
            "AWS_CONFIG_BUCKET": config_bucket.bucket_name,
            "AWS_PUBLIC_BUCKET": config.api.public_bucket,
            "IMAGE_PROCESSING_BUCKET": image_processing_bucket.bucket_name,
            "EMAIL_HOST": config.api.email_host,
            "EMAIL_PORT": config.api.email_port,
            "AUTH0_MANAGEMENT_API_AUDIENCE": config.api.auth0_management_api_audience,
            "MERMAID_API_AUDIENCE": config.api.mermaid_api_audience,
            "MC_USER": config.api.mc_user,
            "DB_NAME": config.database.name,
            "DB_HOST": database.instance_endpoint.hostname,
            "DB_PORT": config.database.port,
            "SQS_MESSAGE_VISIBILITY": str(config.api.sqs_message_visibility),
            "USE_FIFO": use_fifo_queues,
            "SQS_QUEUE_NAME": sqs_queue_name,
            "IMAGE_SQS_QUEUE_NAME": image_sqs_queue_name,
        }

        # build image asset to be shared with API and Backup Task
        image_asset = ecr_assets.DockerImageAsset(
            self,
            "ApiImage",
            directory="../",
            file="Dockerfile",
        )

        backup_task_def = ecs.Ec2TaskDefinition(
            self,
            "ScheduledBackupTaskDef",
            network_mode=ecs.NetworkMode.AWS_VPC,
        )
        backup_task_def.add_container(
            "ScheduledBackupContainer",
            image=ecs.ContainerImage.from_docker_image_asset(image_asset),
            cpu=config.api.backup_cpu,
            memory_limit_mib=config.api.backup_memory,
            secrets=api_secrets,
            environment=environment,
            command=["python", "manage.py", "dbbackup", f"{config.env_id}"],
            logging=ecs.LogDrivers.aws_logs(stream_prefix="ScheduledBackupTask"),
        )

        # create a scheduled fargate task
        backup_task = ecs_patterns.ScheduledEc2Task(
            self,
            "ScheduledBackupTask",
            schedule=appscaling.Schedule.rate(Duration.days(1)),
            cluster=cluster,
            subnet_selection=ec2.SubnetSelection(
                subnets=cluster.vpc.select_subnets(
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_NAT
                ).subnets
            ),
            security_groups=[container_security_group],
            scheduled_ec2_task_definition_options=ecs_patterns.ScheduledEc2TaskDefinitionOptions(
                task_definition=backup_task_def
            ),
        )

        task_definition.add_container(
            id="MermaidAPI",
            image=ecs.ContainerImage.from_docker_image_asset(image_asset),
            cpu=config.api.container_cpu,
            memory_limit_mib=config.api.container_memory,
            port_mappings=[ecs.PortMapping(container_port=8081)],
            environment=environment,
            secrets=api_secrets,
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix=config.env_id, log_retention=logs.RetentionDays.ONE_MONTH
            ),
        )

        service = ecs.Ec2Service(
            self,
            id="ApiService",
            task_definition=task_definition,
            cluster=cluster,
            security_groups=[container_security_group],
            desired_count=config.api.container_count,
            enable_execute_command=True,
            capacity_provider_strategies=[
                ecs.CapacityProviderStrategy(
                    capacity_provider="mermaid-api-infra-common-AsgCapacityProvider760D11D9-iqzBF6LfX313",
                    weight=100,
                )
            ],
        )

        # Grant Secret read to API container & backup task
        for _, container_secret in api_secrets.items():
            container_secret.grant_read(service.task_definition.execution_role)
            container_secret.grant_read(backup_task.task_definition.execution_role)

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

        # create CNAME for ALB
        record = r53.ARecord(
            self,
            "AliasRecord",
            zone=api_zone,
            record_name=f"{config.env_id}.{api_zone.zone_name}",
            target=r53.RecordTarget.from_alias(r53_targets.LoadBalancerTarget(load_balancer)),
        )

        # add rule to SSL listener
        host_headers = [record.domain_name]
        rule_priority = 101

        if config.env_id == "dev":
            host_headers.append("dev-api.datamermaid.org")

        elif config.env_id == "prod":
            rule_priority = 100
            host_headers.append("api.datamermaid.org")

        # add a host header rule
        _ = elb.ApplicationListenerRule(
            self,
            id="HostHeaderListenerRule",
            listener=load_balancer.listeners[0],
            priority=rule_priority,
            conditions=[elb.ListenerCondition.host_headers(host_headers)],
            target_groups=[target_group],
        )

        # Allow API service to read/write to backup bucket in case we want to manually
        # run dbbackup/dbrestore tasks from within the container
        backup_bucket.grant_read_write(service.task_definition.task_role)

        # Give permission to backup task
        backup_bucket.grant_read_write(backup_task.task_definition.task_role)

        # get monitored queue
        worker = QueueWorker(
            self,
            "Worker",
            config=config,
            cluster=cluster,
            image_asset=image_asset,
            container_security_group=container_security_group,
            api_secrets=api_secrets,
            environment=environment,
            public_bucket=public_bucket,
            queue_name=sqs_queue_name,
            email=sys_email,
            fifo=False,
        )

        # get monitored queue
        image_worker = QueueWorker(
            self,
            "ImageWorker",
            config=config,
            cluster=cluster,
            image_asset=image_asset,
            container_security_group=container_security_group,
            api_secrets=api_secrets,
            environment=environment,
            public_bucket=public_bucket,
            queue_name=image_sqs_queue_name,
            email=sys_email,
            fifo=False,
        )

        # allow API to send messages to the queue
        worker.queue.grant_send_messages(service.task_definition.task_role)
        image_worker.queue.grant_send_messages(service.task_definition.task_role)

        # allow API to read/write to the public bucket
        public_bucket.grant_read_write(service.task_definition.task_role)

        # Allow Image Worker to write to image bucket
        image_processing_bucket.grant_write(image_worker.task_definition.task_role)
        image_processing_bucket.grant_read_write(service.task_definition.task_role)

        # Allow Service and Image Worker to read/write config bucket
        config_bucket.grant_read_write(image_worker.task_definition.task_role)
        config_bucket.grant_read_write(service.task_definition.task_role)
