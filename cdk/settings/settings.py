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
class ProjectSettings:
    """Settings Class for Project Envs"""

    # Custom attrs
    cdk_env: Environment
    env_id: str
    database: DatabaseSettings
    

    # Common (default) attrs
    branch_name: str = get_branch_name()
