"""Settings for development environments"""
import os

from aws_cdk import Environment

from cdk.settings.settings import ProjectSettings, VpcSettings

DEV_SETTINGS = ProjectSettings(
    cdk_env=Environment(
        account=os.getenv("DEV_AWS_ACCT", None),
        region=os.getenv("DEV_AWS_REGION", "us-east-1"),
    ),
    env_id="dev",
    # vpc=VpcSettings(
    #     az_count=1,
    #     cidr_block="10.20.0.0/16",
    # ),
)
