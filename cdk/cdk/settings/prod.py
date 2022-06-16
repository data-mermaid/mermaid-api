"""Settings for production environment"""
import os

from aws_cdk import Environment

from cdk.settings.settings import ProjectSettings, VpcSettings

PROD_SETTINGS = ProjectSettings(
    cdk_env=Environment(
        account=os.getenv("PROD_AWS_ACCT", None),
        region=os.getenv("PROD_AWS_REGION", "us-east-1"),
    ),
    env_id="prod",
    # vpc=VpcSettings(
    #     az_count=3,
    #     cidr_block="10.10.0.0/16",
    # ),
)
