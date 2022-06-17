"""
Settings Class
"""
from dataclasses import dataclass

from aws_cdk import Environment, RemovalPolicy, aws_ec2 as ec2

from cdk.settings.utils import get_branch_name


@dataclass
class DatabaseSettings:
    """Settings Class for Postgres Database"""
    name: str
    username: str = "mermaid-svc-user"


@dataclass
class DjangoSettings:
    """Settings Class for Django API"""
    backup_bucket_name: str
    container_cpu: int # See below for values
    container_memory: int # See below for values
    container_count: int




@dataclass
class ProjectSettings:
    """Settings Class for Project Envs"""

    # Custom attrs
    cdk_env: Environment
    env_id: str
    database: DatabaseSettings
    api: DjangoSettings
    

    # Common (default) attrs
    branch_name: str = get_branch_name()


"""
Fargate CPU and Memory values
CPU value	   | Memory value (MiB)
256 (.25 vCPU) | 512 (0.5GB), 1024 (1GB), 2048 (2GB)
512 (.5 vCPU)  | 1024 (1GB), 2048 (2GB), 3072 (3GB), 4096 (4GB)
1024 (1 vCPU)  | 2048 (2GB), 3072 (3GB), 4096 (4GB), 5120 (5GB), 6144 (6GB), 7168 (7GB), 8192 (8GB)
2048 (2 vCPU)  | Between 4096 (4GB) and 16384 (16GB) in increments of 1024 (1GB)
4096 (4 vCPU)  | Between 8192 (8GB) and 30720 (30GB) in increments of 1024 (1GB)
"""