import os
import re

from aws_cdk import (
    Arn,
    ArnComponents,
    ArnFormat,
    Duration,
    Stack,
    aws_applicationautoscaling as appscaling,
    aws_autoscaling as autoscale,
    aws_cloudfront as cf,
    aws_ec2 as ec2,
    aws_ecr_assets as ecr_assets,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_elasticloadbalancingv2 as elb,
    aws_iam as iam,
    aws_logs as logs,
    aws_rds as rds,
    aws_route53 as r53,
    aws_route53_targets as r53_targets,
    aws_s3 as s3,
    aws_secretsmanager as secrets,
    aws_sns as sns,
)
from constructs import Construct
from settings.settings import ProjectSettings
from stacks.constructs.adot import add_adot_sidecar
from stacks.constructs.alerts import MonitoringAlerts
from stacks.constructs.dashboard import MonitoringDashboard
from stacks.constructs.worker import QueueWorker


def camel_case(string: str) -> str:
    s = re.sub(r"(_|-)+", " ", string).title().replace(" ", "")
    return "".join([s[0].lower(), s[1:]])


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
        data_bucket: s3.Bucket,
        public_bucket: s3.Bucket,
        load_balancer: elb.ApplicationLoadBalancer,
        container_security_group: ec2.SecurityGroup,
        api_zone: r53.HostedZone,
        image_processing_bucket: s3.Bucket,
        auto_scaling_group: autoscale.AutoScalingGroup,
        distribution: cf.Distribution,
        sagemaker_domain_name: str,
        use_fifo_queues: str,
        report_s3_creds: secrets.Secret,
        cost_alerts_topic: sns.ITopic | None = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        sys_email = os.environ.get("SYS_EMAIL") or None

        def get_secret_object(stack: Stack, secret_name: str):
            """Return secret object from secret name"""
            construct_id = f"{camel_case(secret_name.split('/')[-1])}"
            return secrets.Secret.from_secret_complete_arn(
                stack,
                id=f"SM-{construct_id}",
                secret_complete_arn=Arn.format(
                    components=ArnComponents(
                        region=stack.region,
                        account=stack.account,
                        partition=stack.partition,
                        resource="secret",
                        service="secretsmanager",
                        resource_name=secret_name,
                        arn_format=ArnFormat.COLON_RESOURCE_NAME,
                    )
                ),
            )

        # Secrets
        env_secret_object = get_secret_object(self, config.api.env_secret_name)
        self.api_secrets = {
            # Created by CDK
            "DB_USER": ecs.Secret.from_secrets_manager(database.secret, "username"),
            "DB_PASSWORD": ecs.Secret.from_secrets_manager(database.secret, "password"),
            "PGPASSWORD": ecs.Secret.from_secrets_manager(database.secret, "password"),
            "REPORT_S3_ACCESS_KEY_ID": ecs.Secret.from_secrets_manager(
                report_s3_creds, "access_key"
            ),
            "REPORT_S3_SECRET_ACCESS_KEY": ecs.Secret.from_secrets_manager(
                report_s3_creds, "secret_key"
            ),
            # Created Manually
            "DRF_RECAPTCHA_SECRET_KEY": ecs.Secret.from_secrets_manager(
                env_secret_object,
                "drf_recaptcha_secret_key",
            ),
            "EMAIL_HOST_USER": ecs.Secret.from_secrets_manager(
                env_secret_object,
                "email_host_user",
            ),
            "EMAIL_HOST_PASSWORD": ecs.Secret.from_secrets_manager(
                env_secret_object,
                "email_host_password",
            ),
            "SECRET_KEY": ecs.Secret.from_secrets_manager(
                env_secret_object,
                "secret_key",
            ),
            "MERMAID_API_SIGNING_SECRET": ecs.Secret.from_secrets_manager(
                env_secret_object,
                "mermaid_api_signing_secret",
            ),
            "SPA_ADMIN_CLIENT_ID": ecs.Secret.from_secrets_manager(
                env_secret_object,
                "spa_admin_client_id",
            ),
            "SPA_ADMIN_CLIENT_SECRET": ecs.Secret.from_secrets_manager(
                env_secret_object,
                "spa_admin_client_secret",
            ),
            "MERMAID_MANAGEMENT_API_CLIENT_ID": ecs.Secret.from_secrets_manager(
                env_secret_object,
                "mermaid_management_api_client_id",
            ),
            "MERMAID_MANAGEMENT_API_CLIENT_SECRET": ecs.Secret.from_secrets_manager(
                env_secret_object,
                "mermaid_management_api_client_secret",
            ),
            "MC_API_KEY": ecs.Secret.from_secrets_manager(
                env_secret_object,
                "mc_api_key",
            ),
            "MC_LIST_ID": ecs.Secret.from_secrets_manager(
                env_secret_object,
                "mc_list_id",
            ),
            "ADMINS": ecs.Secret.from_secrets_manager(
                env_secret_object,
                "admins",
            ),
            "SUPERUSER": ecs.Secret.from_secrets_manager(
                env_secret_object,
                "superuser",
            ),
            "AUTH0_DOMAIN": ecs.Secret.from_secrets_manager(
                env_secret_object,
                "auth0_domain",
            ),
            "IMAGE_BUCKET_AWS_ACCESS_KEY_ID": ecs.Secret.from_secrets_manager(
                env_secret_object,
                "image_bucket_aws_access_key_id",
            ),
            "IMAGE_BUCKET_AWS_SECRET_ACCESS_KEY": ecs.Secret.from_secrets_manager(
                env_secret_object,
                "image_bucket_aws_secret_access_key",
            ),
            "SENTRY_DSN": ecs.Secret.from_secrets_manager(
                env_secret_object,
                "sentry_dsn",
            ),
        }

        if config.env_id == "dev":
            self.api_secrets["DEV_EMAILS"] = ecs.Secret.from_secrets_manager(
                env_secret_object, "dev_emails"
            )

        # Envir Vars
        sqs_queue_name = f"mermaid-{config.env_id}-general"
        image_sqs_queue_name = f"mermaid-{config.env_id}-image-processing"
        environment = {
            "ENV": config.env_id,
            "ENVIRONMENT": config.env_id,
            "ALLOWED_HOSTS": load_balancer.load_balancer_dns_name,
            "MAINTENANCE_MODE": config.api.maintenance_mode,
            "DEFAULT_DOMAIN_API": config.api.default_domain_api,
            "DEFAULT_DOMAIN_COLLECT": config.api.default_domain_collect,
            "AWS_BACKUP_BUCKET": backup_bucket.bucket_name,
            "AWS_CONFIG_BUCKET": config_bucket.bucket_name,
            "AWS_DATA_BUCKET": data_bucket.bucket_name,
            "AWS_PUBLIC_BUCKET": config.api.public_bucket,
            "IMAGE_PROCESSING_BUCKET": config.api.ic_bucket_name,
            "IMAGE_PROCESSING_BUCKET_TEST": config.api.ic_bucket_name_test
            or config.api.ic_bucket_name,
            "IMAGE_S3_PATH_TEST": config.api.ic_s3_path_test or "mermaid/",
            "IMAGE_PROCESSING_BUCKET_DUMMY": image_processing_bucket.bucket_name,
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
            # OpenTelemetry / X-Ray
            # ecs-xray.yaml only configures a traces pipeline; disable metrics and
            # logs exporters to suppress UNIMPLEMENTED errors from the ADOT sidecar.
            "OTEL_TRACES_EXPORTER": "otlp",
            "OTEL_METRICS_EXPORTER": "none",
            "OTEL_LOGS_EXPORTER": "none",
            "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317",
            "OTEL_PROPAGATORS": "xray",
            "OTEL_PYTHON_ID_GENERATOR": "xray",
        }

        # build image asset to be shared with API and Backup Task
        image_asset = ecr_assets.DockerImageAsset(
            self,
            "ApiImage",
            directory="../",
            file="Dockerfile",
        )

        # --- Scheduled Backup Task ---

        daily_task_def = ecs.FargateTaskDefinition(
            self,
            "ScheduledBackupTaskDef",
            cpu=config.api.backup_cpu,
            memory_limit_mib=config.api.backup_memory,
        )
        daily_task_def.add_container(
            "ScheduledBackupContainer",
            image=ecs.ContainerImage.from_docker_image_asset(image_asset),
            cpu=config.api.backup_cpu,
            memory_limit_mib=config.api.backup_memory,
            secrets=self.api_secrets,
            environment={**environment, "OTEL_SERVICE_NAME": f"mermaid-backup-{config.env_id}"},
            command=["opentelemetry-instrument", "python", "manage.py", "daily_tasks"],
            logging=ecs.LogDrivers.aws_logs(stream_prefix="ScheduledBackupTask"),
        )
        add_adot_sidecar(daily_task_def, "Backup")

        daily_backup_task = ecs_patterns.ScheduledFargateTask(
            self,
            "ScheduledBackupTask",
            schedule=appscaling.Schedule.cron(hour="0", minute="0"),
            cluster=cluster,
            subnet_selection=ec2.SubnetSelection(
                subnets=cluster.vpc.select_subnets(
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
                ).subnets
            ),
            security_groups=[container_security_group],
            scheduled_fargate_task_definition_options=ecs_patterns.ScheduledFargateTaskDefinitionOptions(
                task_definition=daily_task_def
            ),
        )

        # --- Summary Cache Update Task ---

        summary_cache_task_def = ecs.Ec2TaskDefinition(
            self,
            "SummaryCacheTaskDef",
            network_mode=ecs.NetworkMode.AWS_VPC,
        )
        summary_cache_task_def.add_container(
            "SummaryCacheUpdateContainer",
            image=ecs.ContainerImage.from_docker_image_asset(image_asset),
            cpu=config.api.summary_cpu,
            memory_limit_mib=config.api.summary_memory,
            secrets=self.api_secrets,
            environment={**environment, "OTEL_SERVICE_NAME": f"mermaid-summary-cache-{config.env_id}"},
            command=["opentelemetry-instrument", "python", "manage.py", "process_summaries"],
            logging=ecs.LogDrivers.aws_logs(stream_prefix="SummaryCacheUpdateContainer"),
        )
        add_adot_sidecar(summary_cache_task_def, "SummaryCache")

        summary_cache_service = ecs.Ec2Service(
            self,
            id="SummaryCacheService",
            task_definition=summary_cache_task_def,
            cluster=cluster,
            security_groups=[container_security_group],
            enable_execute_command=True,
            min_healthy_percent=0,
            capacity_provider_strategies=cluster.default_capacity_provider_strategy,
            circuit_breaker=ecs.DeploymentCircuitBreaker(enable=True, rollback=True),
        )

        # --- API Service ---

        task_definition = ecs.Ec2TaskDefinition(
            self, id="ApiTaskDefinition", network_mode=ecs.NetworkMode.AWS_VPC
        )
        api_log_group = logs.LogGroup.from_log_group_name(
            self,
            "ApiLogGroup",
            f"/mermaid/{config.env_id}/api",
        )
        task_definition.add_container(
            id="MermaidAPI",
            image=ecs.ContainerImage.from_docker_image_asset(image_asset),
            cpu=config.api.container_cpu,
            memory_limit_mib=config.api.container_memory,
            port_mappings=[ecs.PortMapping(container_port=8081)],
            environment={**environment, "OTEL_SERVICE_NAME": f"mermaid-api-{config.env_id}"},
            secrets=self.api_secrets,
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix=config.env_id,
                log_group=api_log_group,
            ),
        )
        add_adot_sidecar(task_definition, "Api")

        service = ecs.Ec2Service(
            self,
            id="ApiService",
            task_definition=task_definition,
            cluster=cluster,
            security_groups=[container_security_group],
            desired_count=config.api.container_count,
            enable_execute_command=True,
            min_healthy_percent=0,
            capacity_provider_strategies=cluster.default_capacity_provider_strategy,
            circuit_breaker=ecs.DeploymentCircuitBreaker(enable=True, rollback=True),
        )

        # Grant Secret read to API container & backup task
        for _, container_secret in self.api_secrets.items():
            container_secret.grant_read(service.task_definition.execution_role)
            container_secret.grant_read(daily_backup_task.task_definition.execution_role)
            container_secret.grant_read(summary_cache_service.task_definition.execution_role)

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
        backup_bucket.grant_read_write(daily_backup_task.task_definition.task_role)

        # Standard Worker
        worker = QueueWorker(
            self,
            "General",
            config=config,
            cluster=cluster,
            image_asset=ecs.ContainerImage.from_docker_image_asset(image_asset),
            api_secrets=self.api_secrets,
            environment={**environment, "OTEL_SERVICE_NAME": f"mermaid-worker-{config.env_id}"},
            public_bucket=public_bucket,
            queue_name=sqs_queue_name,
            email=sys_email,
            fifo=False,
        )

        # Image Worker
        image_worker = QueueWorker(
            self,
            "ImageProcess",
            config=config,
            cluster=cluster,
            image_asset=ecs.ContainerImage.from_docker_image_asset(image_asset),
            api_secrets=self.api_secrets,
            environment={**environment, "OTEL_SERVICE_NAME": f"mermaid-image-worker-{config.env_id}"},
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
        # General worker needs read/write for image migration jobs between buckets
        image_processing_bucket.grant_read_write(worker.task_definition.task_role)

        # Allow Service and Image Worker to read/write config bucket
        config_bucket.grant_read_write(image_worker.task_definition.task_role)
        config_bucket.grant_read_write(worker.task_definition.task_role)
        config_bucket.grant_read_write(service.task_definition.task_role)

        # Allow Service and Image Worker to read/write config bucket
        data_bucket.grant_read_write(image_worker.task_definition.task_role)
        data_bucket.grant_read_write(worker.task_definition.task_role)
        data_bucket.grant_read_write(service.task_definition.task_role)
        data_bucket.grant_read_write(summary_cache_service.task_definition.task_role)
        data_bucket.grant_delete(summary_cache_service.task_definition.task_role)
        # Prod bucket needs to read from coral-reef-training bucket.
        # There is some issue with assumed-role reading from public bucket,
        # adding read permission to the task role seems to fix it.
        coral_reef_training_bucket = s3.Bucket.from_bucket_name(
            self,
            "CoralReefBucket",
            bucket_name=config.api.ic_bucket_name,
        )
        coral_reef_training_bucket.grant_read(service.task_definition.task_role)
        coral_reef_training_bucket.grant_read(image_worker.task_definition.task_role)
        coral_reef_training_bucket.grant_read_write(worker.task_definition.task_role)
        # Backup task needs read/write on the primary image bucket for delete_orphaned_images
        # and export_annotations_parquet (dev: mermaid-image-processing, prod: coral-reef-training).
        # Scoped to the app-managed prefix (IMAGE_S3_PATH = "mermaid/").
        coral_reef_training_bucket.grant_read_write(
            daily_backup_task.task_definition.task_role, "mermaid/*"
        )
        # In prod, mermaid-image-processing (the test-project image bucket) is separate from
        # coral-reef-training; grant the backup task role access to it for orphaned test images.
        # Scoped to IMAGE_S3_PATH_TEST (ic_s3_path_test = "mermaid-production-test/").
        if config.api.ic_bucket_name_test:
            image_processing_test_bucket = s3.Bucket.from_bucket_name(
                self,
                "ImageProcessingTestBucketForBackup",
                bucket_name=config.api.ic_bucket_name_test,
            )
            image_processing_test_bucket.grant_read_write(
                daily_backup_task.task_definition.task_role,
                f"{config.api.ic_s3_path_test}*",
            )

        # ── CloudWatch Dashboard ─────────────────────────────────────
        MonitoringDashboard(
            self,
            "Monitoring",
            env_id=config.env_id,
            load_balancer=load_balancer,
            api_service=service,
            summary_cache_service=summary_cache_service,
            general_worker_service=worker.service,
            image_worker_service=image_worker.service,
            database=database,
            general_queue=worker.queue,
            general_dlq_queue=worker.dead_letter_queue,
            image_queue=image_worker.queue,
            image_dlq_queue=image_worker.dead_letter_queue,
            auto_scaling_group=auto_scaling_group,
            vpc=cluster.vpc,
            buckets=[backup_bucket, config_bucket, data_bucket, image_processing_bucket],
            distribution=distribution,
            sagemaker_domain_name=sagemaker_domain_name,
        )

        # ── CloudWatch Alarms + Slack (AWS Chatbot) ──────────────────
        monitoring_alerts = MonitoringAlerts(
            self,
            "Alerts",
            env_id=config.env_id,
            load_balancer=load_balancer,
            api_service=service,
            database=database,
            general_dlq=worker.dead_letter_queue,
            image_dlq=image_worker.dead_letter_queue,
            api_log_group=api_log_group,
            sagemaker_domain_name=sagemaker_domain_name,
            slack_workspace_id=config.api.slack_workspace_id or None,
            slack_channel_id=config.api.slack_channel_id or None,
            cost_alerts_topic=cost_alerts_topic,
        )
        # Exposed so sibling stacks (e.g. InferenceStack) can publish alarms to
        # the same per-env topic this stack's Chatbot config already delivers.
        self.alerts_topic = monitoring_alerts.topic
