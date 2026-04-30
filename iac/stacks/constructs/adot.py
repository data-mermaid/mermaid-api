from aws_cdk import aws_ecs as ecs, aws_iam as iam

ADOT_IMAGE = "public.ecr.aws/aws-observability/aws-otel-collector:v0.47.0"


def add_adot_sidecar(task_def: ecs.TaskDefinition, name: str) -> None:
    task_def.add_container(
        f"{name}AdotCollector",
        image=ecs.ContainerImage.from_registry(ADOT_IMAGE),
        cpu=32,
        memory_limit_mib=256,
        essential=False,
        command=["--config=/etc/ecs/ecs-xray.yaml"],
        port_mappings=[
            ecs.PortMapping(container_port=4317, protocol=ecs.Protocol.TCP),
            ecs.PortMapping(container_port=4318, protocol=ecs.Protocol.TCP),
            ecs.PortMapping(container_port=2000, protocol=ecs.Protocol.UDP),
        ],
        logging=ecs.LogDrivers.aws_logs(stream_prefix=f"{name}-adot"),
    )
    task_def.task_role.add_managed_policy(
        iam.ManagedPolicy.from_aws_managed_policy_name("AWSXRayDaemonWriteAccess")
    )
