import os

from aws_cdk import App, Environment
from settings.dev import DEV_SETTINGS
from settings.prod import PROD_SETTINGS
from stacks.api import ApiStack
from stacks.common import CommonStack
from stacks.github_access import GithubAccessStack
from stacks.sagemaker import SagemakerStack
from stacks.static_site import StaticSiteStack

tags = {
    "Owner": "sysadmin@datamermaid.org",
    # "Environment": PROJECT_SETTINGS.env_id,
    # "Git Branch": PROJECT_SETTINGS.branch_name,
}


app = App()

cdk_env = Environment(
    account=os.getenv("CDK_DEFAULT_ACCOUNT", None),
    region=os.getenv("CDK_DEFAULT_REGION", "us-east-1"),
)

gh_access_stack = GithubAccessStack(
    app,
    "GithubAccess",
    env=cdk_env,
    tags={"Env": "Common"},
    cross_region_references=True,
)


common_stack = CommonStack(
    app,
    "mermaid-api-infra-common",
    env=cdk_env,
    tags=tags,
)

dev_static_site_stack = StaticSiteStack(
    app,
    "dev-mermaid-static-site",
    env=cdk_env,
    tags=tags,
    config=DEV_SETTINGS,
    default_cert=common_stack.default_cert,
)

dev_api_stack = ApiStack(
    app,
    "dev-mermaid-api-django",
    env=cdk_env,
    tags=tags,
    config=DEV_SETTINGS,
    cluster=common_stack.cluster,
    database=common_stack.database,
    backup_bucket=common_stack.backup_bucket,
    data_bucket=common_stack.data_bucket,
    config_bucket=common_stack.config_bucket,
    load_balancer=common_stack.load_balancer,
    container_security_group=common_stack.ecs_sg,
    api_zone=common_stack.api_zone,
    public_bucket=dev_static_site_stack.site_bucket,
    image_processing_bucket=common_stack.image_processing_bucket,
    use_fifo_queues="False",
    report_s3_creds=common_stack.report_s3_creds,
)

dev_sagemaker_stack = SagemakerStack(
    app,
    "dev-mermaid-sagemaker",
    env=cdk_env,
    tags=tags,
    config=DEV_SETTINGS,
    cluster=common_stack.cluster,
)

prod_static_site_stack = StaticSiteStack(
    app,
    "prod-mermaid-static-site",
    env=cdk_env,
    tags=tags,
    config=PROD_SETTINGS,
    default_cert=common_stack.default_cert,
)

prod_api_stack = ApiStack(
    app,
    "prod-mermaid-api-django",
    env=cdk_env,
    tags=tags,
    config=PROD_SETTINGS,
    cluster=common_stack.cluster,
    database=common_stack.database,
    backup_bucket=common_stack.backup_bucket,
    data_bucket=common_stack.data_bucket,
    config_bucket=common_stack.config_bucket,
    load_balancer=common_stack.load_balancer,
    container_security_group=common_stack.ecs_sg,
    api_zone=common_stack.api_zone,
    public_bucket=prod_static_site_stack.site_bucket,
    image_processing_bucket=common_stack.image_processing_bucket,
    use_fifo_queues="False",
    report_s3_creds=common_stack.report_s3_creds,
)


app.synth()
