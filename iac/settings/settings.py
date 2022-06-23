"""
Settings Class
"""
import os
from dataclasses import dataclass

from aws_cdk import Environment, RemovalPolicy, aws_ec2 as ec2

from iac.settings.utils import get_branch_name


@dataclass
class DatabaseSettings:
    """Settings Class for Postgres Database"""
    name: str
    username: str = "mermaid_admin"


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
    allowed_hosts: str
    default_domain_api: str
    default_domain_collect: str
    mermaid_api_audience: str
    
    # Common Attrs (defaults)
    superuser: str = "contact@datamermaid.org"
    admins: str = "sysadmin@datamermaid.org"
    maintenance_mode: str = "False"
    auth0_management_api_audience: str = "https://datamermaid.auth0.com/api/v2/"
    aws_backup_bucket_name: str = "mermaid-api-v2-backups" # Use CDK construct?
    email_host: str = "smtp.gmail.com"
    email_port: str = "587"
    email_host_user: str = "sysadmin@datamermaid.org"
    mc_user: str = "Mermaid"

    # Common Secrets
    secret_key_name: str = "common/mermaid-api/secret"
    email_host_password_name: str = "common/mermaid-api/email-host-password"
    mermaid_api_signing_secret_name: str = "common/mermaid-api/mermaid-api-signing-secret"
    spa_admin_client_name: str = "common/mermaid-api/spa-admin-client"
    mermaid_management_api_client_name: str = "common/mermaid-api/mermaid-management-api-client"
    mc_api_key_name: str = "common/mermaid-api/mc-api-key"


@dataclass
class ProjectSettings:
    """Settings Class for Project Envs"""

    # Dynamic Attrs
    cdk_env: Environment
    env_id: str
    database: DatabaseSettings
    api: DjangoSettings
    

    # Common Attrs (defaults)
    branch_name: str = get_branch_name()
