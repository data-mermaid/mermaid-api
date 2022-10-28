"""
Settings Class
"""
import os
from dataclasses import dataclass

from aws_cdk import (
    Environment,
    Stack,
    Arn,
    ArnComponents,
    ArnFormat,
    aws_ec2 as ec2,
    aws_secretsmanager as secrets,
)

from iac.settings.utils import camel_case


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
    default_domain_api: str
    default_domain_collect: str
    mermaid_api_audience: str

    # Dynamic Secrets
    dev_emails_name: str = ""

    # Common Attrs (defaults)
    maintenance_mode: str = "False"
    auth0_management_api_audience: str = "https://datamermaid.auth0.com/api/v2/"
    email_host: str = "smtp.gmail.com"
    email_port: str = "587"
    mc_user: str = "Mermaid"

    # Common Secrets
    superuser_name: str = "common/mermaid-api/superuser-u3SSj4"
    admins_name: str = "common/mermaid-api/admins-z5Y80V"
    secret_key_name: str = "common/mermaid-api/secret-OcuWCl"
    email_host_user_name: str = "common/mermaid-api/email-host-user-afLrHz"
    email_host_password_name: str = "common/mermaid-api/email-host-password-CI6hBI"
    mermaid_api_signing_secret_name: str = (
        "common/mermaid-api/mermaid-api-signing-secret-FM7ATI"
    )

    spa_admin_client_id_name: str = "common/mermaid-api/spa-admin-client-id-FuMVtc"
    spa_admin_client_secret_name: str = (
        "common/mermaid-api/spa-admin-client-secret-kYccw0"
    )
    mermaid_management_api_client_id_name: str = (
        "common/mermaid-api/mermaid-management-api-client-id-nIWaxV"
    )
    mermaid_management_api_client_secret_name: str = (
        "common/mermaid-api/mermaid-management-api-client-secret-HNVoT0"
    )
    mc_api_key_name: str = "common/mermaid-api/mc-api-key-xSsQOk"
    mc_api_list_id_name: str = "common/mermaid-api/mc-api-list-id-Am5u1G"
    drf_recaptcha_secret_key_name: str = "common/mermaid-api/drf-recaptcha-secret-key-MdFr2W"

    def get_secret_object(self, stack: Stack, secret_name: str):
        """Return secret object from name and field"""
        id = f'{camel_case(secret_name.split("/")[-1])}'
        return secrets.Secret.from_secret_complete_arn(
            stack,
            id=f"SSM-{id}",
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


@dataclass
class ProjectSettings:
    """Settings Class for Project Envs"""

    # Dynamic Attrs
    env_id: str
    database: DatabaseSettings
    api: DjangoSettings
