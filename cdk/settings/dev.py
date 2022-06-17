"""Settings for development environments"""
import os

from aws_cdk import Environment

from cdk.settings.settings import DatabaseSettings, ProjectSettings

DEV_ENV_ID = "dev"
DEV_SETTINGS = ProjectSettings(
    cdk_env=Environment(
        account=os.getenv("DEV_AWS_ACCT", None),
        region=os.getenv("DEV_AWS_REGION", "us-east-1"),
    ),
    env_id="dev",
    database=DatabaseSettings(
        name=f'{DEV_ENV_ID}-mermaid',
    )
)
