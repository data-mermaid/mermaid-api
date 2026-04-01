from aws_cdk import (
    Duration,
    aws_cloudwatch as cw,
    aws_ecs as ecs,
    aws_elasticloadbalancingv2 as elb,
    aws_rds as rds,
    aws_sqs as sqs,
)
from constructs import Construct


class MonitoringDashboard(Construct):
    """CloudWatch dashboard providing an at-a-glance view of system health."""

    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        env_id: str,
        load_balancer: elb.IApplicationLoadBalancer,
        api_service: ecs.Ec2Service,
        summary_cache_service: ecs.Ec2Service,
        general_worker_service: ecs.Ec2Service,
        image_worker_service: ecs.Ec2Service,
        database: rds.DatabaseInstance,
        general_queue: sqs.IQueue,
        general_dlq_queue: sqs.IQueue,
        image_queue: sqs.IQueue,
        image_dlq_queue: sqs.IQueue,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        dashboard = cw.Dashboard(
            self,
            "Dashboard",
            dashboard_name=f"mermaid-{env_id}-system-health",
            default_interval=Duration.hours(3),
        )

        # ── ALB Widgets ──────────────────────────────────────────────

        alb_metrics = load_balancer.metrics

        alb_request_count = cw.GraphWidget(
            title="ALB Request Count",
            left=[
                alb_metrics.request_count(statistic="Sum"),
            ],
            width=8,
        )

        alb_5xx = cw.GraphWidget(
            title="ALB 5xx Errors",
            left=[
                alb_metrics.http_code_target(
                    code=elb.HttpCodeTarget.TARGET_5XX_COUNT,
                    statistic="Sum",
                ),
                alb_metrics.http_code_elb(
                    code=elb.HttpCodeElb.ELB_5XX_COUNT,
                    statistic="Sum",
                ),
            ],
            width=8,
        )

        alb_latency = cw.GraphWidget(
            title="ALB Latency (p50 / p99)",
            left=[
                alb_metrics.target_response_time(statistic="p50"),
                alb_metrics.target_response_time(statistic="p99"),
            ],
            width=8,
        )

        # ── ECS Widgets ──────────────────────────────────────────────

        ecs_services = {
            "API": api_service,
            "SummaryCache": summary_cache_service,
            "GeneralWorker": general_worker_service,
            "ImageWorker": image_worker_service,
        }

        ecs_cpu = cw.GraphWidget(
            title="ECS CPU Utilization",
            left=[
                svc.metric_cpu_utilization(label=name)
                for name, svc in ecs_services.items()
            ],
            width=12,
        )

        ecs_memory = cw.GraphWidget(
            title="ECS Memory Utilization",
            left=[
                svc.metric_memory_utilization(label=name)
                for name, svc in ecs_services.items()
            ],
            width=12,
        )

        # ── RDS Widgets ──────────────────────────────────────────────

        rds_cpu = cw.GraphWidget(
            title="RDS CPU Utilization",
            left=[database.metric_cpu_utilization()],
            width=8,
        )

        rds_connections = cw.GraphWidget(
            title="RDS Database Connections",
            left=[database.metric_database_connections()],
            width=8,
        )

        rds_iops = cw.GraphWidget(
            title="RDS Read / Write IOPS",
            left=[
                database.metric("ReadIOPS", statistic="Average"),
                database.metric("WriteIOPS", statistic="Average"),
            ],
            width=8,
        )

        # ── SQS Widgets ──────────────────────────────────────────────

        sqs_depth = cw.GraphWidget(
            title="SQS Queue Depth",
            left=[
                general_queue.metric_approximate_number_of_messages_visible(
                    label="General",
                    statistic="Maximum",
                ),
                image_queue.metric_approximate_number_of_messages_visible(
                    label="ImageProcessing",
                    statistic="Maximum",
                ),
            ],
            width=8,
        )

        sqs_messages = cw.GraphWidget(
            title="SQS Messages Sent / Received",
            left=[
                general_queue.metric_number_of_messages_sent(
                    label="General Sent", statistic="Sum"
                ),
                general_queue.metric_number_of_messages_received(
                    label="General Received", statistic="Sum"
                ),
                image_queue.metric_number_of_messages_sent(
                    label="Image Sent", statistic="Sum"
                ),
                image_queue.metric_number_of_messages_received(
                    label="Image Received", statistic="Sum"
                ),
            ],
            width=8,
        )

        sqs_dlq = cw.GraphWidget(
            title="DLQ Depth",
            left=[
                general_dlq_queue.metric_approximate_number_of_messages_visible(
                    label="General DLQ",
                    statistic="Maximum",
                ),
                image_dlq_queue.metric_approximate_number_of_messages_visible(
                    label="Image DLQ",
                    statistic="Maximum",
                ),
            ],
            width=8,
        )

        # ── Assemble Dashboard ───────────────────────────────────────

        dashboard.add_widgets(
            cw.TextWidget(markdown="## ALB", width=24, height=1),
        )
        dashboard.add_widgets(alb_request_count, alb_5xx, alb_latency)

        dashboard.add_widgets(
            cw.TextWidget(markdown="## ECS Services", width=24, height=1),
        )
        dashboard.add_widgets(ecs_cpu, ecs_memory)

        dashboard.add_widgets(
            cw.TextWidget(markdown="## RDS", width=24, height=1),
        )
        dashboard.add_widgets(rds_cpu, rds_connections, rds_iops)

        dashboard.add_widgets(
            cw.TextWidget(markdown="## SQS", width=24, height=1),
        )
        dashboard.add_widgets(sqs_depth, sqs_messages, sqs_dlq)
