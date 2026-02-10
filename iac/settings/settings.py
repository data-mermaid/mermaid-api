"""
Settings Class
"""

from dataclasses import dataclass


@dataclass
class DatabaseSettings:
    """Settings Class for Postgres Database"""

    name: str
    port: str


@dataclass
class DjangoSettings:
    """Settings Class for Django API
    Fargate CPU and Memory values
    CPU value	   | Memory value (MiB)
    256 (.25 vCPU) | 512 (0.5GB), 1024 (1GB), 2048 (2GB)
    512 (.5 vCPU)  | 1024 (1GB), 2048 (2GB), 3072 (3GB), 4096 (4GB)
    1024 (1 vCPU)  | 2048 (2GB), 3072 (3GB), 4096 (4GB), 5120 (5GB), 6144 (6GB), 7168 (7GB), 8192 (8GB)
    2048 (2 vCPU)  | Between 4096 (4GB) and 16384 (16GB) in increments of 1024 (1GB)
    4096 (4 vCPU)  | Between 8192 (8GB) and 30720 (30GB) in increments of 1024 (1GB)
    """

    # Dynamic Attrs
    container_cpu: int
    container_memory: int
    container_count: int

    sqs_cpu: int
    sqs_memory: int

    backup_cpu: int
    backup_memory: int

    summary_cpu: int
    summary_memory: int

    default_domain_api: str
    default_domain_collect: str
    mermaid_api_audience: str
    public_bucket: str
    sqs_message_visibility: int

    ic_bucket_name: str

    # Secrets
    env_secret: str

    # Common Attrs (defaults)
    maintenance_mode: str = "False"
    auth0_management_api_audience: str = "https://datamermaid.auth0.com/api/v2/"
    email_host: str = "smtp.gmail.com"
    email_port: str = "587"
    mc_user: str = "Mermaid"


@dataclass
class ProjectSettings:
    """Settings Class for Project Envs"""

    # Dynamic Attrs
    env_id: str
    database: DatabaseSettings
    api: DjangoSettings
