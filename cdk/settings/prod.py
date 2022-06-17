"""Settings for production environment"""
import os

from aws_cdk import Environment, RemovalPolicy, aws_ec2 as ec2

from cdk.settings.settings import DatabaseSettings, ProjectSettings

PROD_ENV_ID = "prod"
PROD_SETTINGS = ProjectSettings(
    cdk_env=Environment(
        account=os.getenv("PROD_AWS_ACCT", None),
        region=os.getenv("PROD_AWS_REGION", "us-east-1"),
    ),
    env_id=PROD_ENV_ID,
    database=DatabaseSettings(
        name=f'{PROD_ENV_ID}-mermaid', # TODO, Change name??
    )
)
