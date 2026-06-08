from aws_cdk import (
    Duration,
    aws_autoscaling as autoscale,
    aws_cloudfront as cf,
    aws_cloudwatch as cw,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_elasticloadbalancingv2 as elb,
    aws_rds as rds,
    aws_s3 as s3,
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
        auto_scaling_group: autoscale.AutoScalingGroup,
        vpc: ec2.IVpc,
        buckets: list[s3.Bucket],
        distribution: cf.Distribution,
        sagemaker_domain_name: str,
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

        # ── NAT Gateway Widgets ──────────────────────────────────────

        # VPC has a single NAT gateway; use metric search to avoid
        # hard-coding the NAT Gateway ID.
        nat_ns = "AWS/NATGateway"

        nat_connections = cw.GraphWidget(
            title="NAT Gateway Active Connections",
            left=[
                cw.Metric(
                    namespace=nat_ns,
                    metric_name="ActiveConnectionCount",
                    statistic="Maximum",
                ),
            ],
            width=8,
        )

        nat_bytes = cw.GraphWidget(
            title="NAT Gateway Bytes Processed",
            left=[
                cw.Metric(
                    namespace=nat_ns,
                    metric_name="BytesInFromSource",
                    statistic="Sum",
                    label="In (source)",
                ),
                cw.Metric(
                    namespace=nat_ns,
                    metric_name="BytesOutToDestination",
                    statistic="Sum",
                    label="Out (destination)",
                ),
            ],
            width=8,
        )

        nat_errors = cw.GraphWidget(
            title="NAT Gateway Errors & Drops",
            left=[
                cw.Metric(
                    namespace=nat_ns,
                    metric_name="ErrorPortAllocation",
                    statistic="Sum",
                    label="Port Allocation Errors",
                ),
                cw.Metric(
                    namespace=nat_ns,
                    metric_name="PacketsDropCount",
                    statistic="Sum",
                    label="Packets Dropped",
                ),
            ],
            width=8,
        )

        dashboard.add_widgets(
            cw.TextWidget(markdown="## NAT Gateway", width=24, height=1),
        )
        dashboard.add_widgets(nat_connections, nat_bytes, nat_errors)

        # ── ASG Widgets ──────────────────────────────────────────────

        asg_dims = {"AutoScalingGroupName": auto_scaling_group.auto_scaling_group_name}

        asg_capacity = cw.GraphWidget(
            title="ASG Instance Count",
            left=[
                cw.Metric(
                    namespace="AWS/AutoScaling",
                    metric_name="GroupInServiceInstances",
                    dimensions_map=asg_dims,
                    statistic="Average",
                    label="In Service",
                ),
                cw.Metric(
                    namespace="AWS/AutoScaling",
                    metric_name="GroupDesiredCapacity",
                    dimensions_map=asg_dims,
                    statistic="Average",
                    label="Desired",
                ),
            ],
            width=12,
        )

        asg_activity = cw.GraphWidget(
            title="ASG Scaling Activity",
            left=[
                cw.Metric(
                    namespace="AWS/AutoScaling",
                    metric_name="GroupPendingInstances",
                    dimensions_map=asg_dims,
                    statistic="Average",
                    label="Pending",
                ),
                cw.Metric(
                    namespace="AWS/AutoScaling",
                    metric_name="GroupTerminatingInstances",
                    dimensions_map=asg_dims,
                    statistic="Average",
                    label="Terminating",
                ),
            ],
            width=12,
        )

        dashboard.add_widgets(
            cw.TextWidget(markdown="## Auto Scaling Group", width=24, height=1),
        )
        dashboard.add_widgets(asg_capacity, asg_activity)

        # ── S3 Widgets ───────────────────────────────────────────────
        # BucketSizeBytes and NumberOfObjects are daily storage metrics
        # emitted automatically (no request metrics configuration needed).

        s3_size = cw.GraphWidget(
            title="S3 Bucket Size (bytes)",
            left=[
                cw.Metric(
                    namespace="AWS/S3",
                    metric_name="BucketSizeBytes",
                    statistic="Average",
                    label=bucket.bucket_name,
                    dimensions_map={
                        "BucketName": bucket.bucket_name,
                        "StorageType": "StandardStorage",
                    },
                    period=Duration.days(1),
                )
                for bucket in buckets
            ],
            width=12,
        )

        s3_objects = cw.GraphWidget(
            title="S3 Object Count",
            left=[
                cw.Metric(
                    namespace="AWS/S3",
                    metric_name="NumberOfObjects",
                    statistic="Average",
                    label=bucket.bucket_name,
                    dimensions_map={
                        "BucketName": bucket.bucket_name,
                        "StorageType": "AllStorageTypes",
                    },
                    period=Duration.days(1),
                )
                for bucket in buckets
            ],
            width=12,
        )

        dashboard.add_widgets(
            cw.TextWidget(markdown="## S3", width=24, height=1),
        )
        dashboard.add_widgets(s3_size, s3_objects)

        # ── CloudFront Widgets ───────────────────────────────────────

        cf_requests = cw.GraphWidget(
            title="CloudFront Requests",
            left=[
                distribution.metric_requests(statistic="Sum"),
            ],
            width=8,
        )

        cf_errors = cw.GraphWidget(
            title="CloudFront Error Rate (%)",
            left=[
                distribution.metric("4xxErrorRate", statistic="Average", label="4xx"),
                distribution.metric("5xxErrorRate", statistic="Average", label="5xx"),
            ],
            width=8,
        )

        cf_bytes = cw.GraphWidget(
            title="CloudFront Bytes Transferred",
            left=[
                distribution.metric("BytesDownloaded", statistic="Sum", label="Downloaded"),
                distribution.metric("BytesUploaded", statistic="Sum", label="Uploaded"),
            ],
            width=8,
        )

        dashboard.add_widgets(
            cw.TextWidget(markdown="## CloudFront", width=24, height=1),
        )
        dashboard.add_widgets(cf_requests, cf_errors, cf_bytes)

        # ── SageMaker Widgets ────────────────────────────────────────
        # SageMaker Studio domain metrics — track active usage.

        sm_ns = "/aws/sagemaker/Domains"

        sm_apps = cw.GraphWidget(
            title="SageMaker Running Apps",
            left=[
                cw.Metric(
                    namespace=sm_ns,
                    metric_name="RunningAppCount",
                    statistic="Maximum",
                    dimensions_map={"DomainName": sagemaker_domain_name},
                    label="Running Apps",
                ),
            ],
            width=12,
        )

        sm_instances = cw.GraphWidget(
            title="SageMaker Running Instances",
            left=[
                cw.Metric(
                    namespace=sm_ns,
                    metric_name="RunningInstanceCount",
                    statistic="Maximum",
                    dimensions_map={"DomainName": sagemaker_domain_name},
                    label="Running Instances",
                ),
            ],
            width=12,
        )

        dashboard.add_widgets(
            cw.TextWidget(markdown="## SageMaker", width=24, height=1),
        )
        dashboard.add_widgets(sm_apps, sm_instances)
