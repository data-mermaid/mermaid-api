"""Settings for production environment"""
import os

from aws_cdk import Environment

from iac.settings.settings import DatabaseSettings, ProjectSettings, DjangoSettings

PROD_ENV_ID = "prod"
# PROD_SETTINGS = ProjectSettings(
#     cdk_env=Environment(
#         account=os.getenv("CDK_DEFAULT_ACCOUNT", None),
#         region=os.getenv("CDK_DEFAULT_REGION", "us-east-1"),
#     ),
#     env_id=PROD_ENV_ID,
#     database=DatabaseSettings(
#         name=f'{PROD_ENV_ID}-mermaid', # TODO, Change name??
#     ),
#     api=DjangoSettings(
#         backup_bucket_name="",
#         container_cpu=1024,
#         container_memory=2048,
#         container_count=1
#     )
# )
