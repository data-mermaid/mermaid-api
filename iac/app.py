import os

from aws_cdk import App, Environment
from iac.stacks.common import CommonStack
from iac.stacks.api import ApiStack
from iac.stacks.static_site import StaticSiteStack
from iac.settings.dev import DEV_SETTINGS
from iac.settings.prod import PROD_SETTINGS

tags = {
    "Owner": "sysadmin@datamermaid.org",
    # "Environment": PROJECT_SETTINGS.env_id,
    # "Git Branch": PROJECT_SETTINGS.branch_name,
}


app = App()

cdk_env=Environment(
    account=os.getenv("CDK_DEFAULT_ACCOUNT", None),
    region=os.getenv("CDK_DEFAULT_REGION", "us-east-1"),
)

common_stack = CommonStack(
    app,
    f"mermaid-api-infra-common",
    env=cdk_env,
    tags=tags,
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
    load_balancer=common_stack.load_balancer,
    container_security_group=common_stack.ecs_sg,
    api_zone=common_stack.api_zone,
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
    load_balancer=common_stack.load_balancer,
    container_security_group=common_stack.ecs_sg,
    api_zone=common_stack.api_zone,
)



# domain_name
# sub_domain_name
# enable_s3_website_endpoint
# domain_certificate_arn
# hosted_zone_id
# hosted_zone_name

props = {
    "namespace": "mermaid",
    "domain_name": "datamermaid.org",
    "sub_domain_name": "dev-public",
    "domain_certificate_arn": app.node.try_get_context(
        "domain_certificate_arn"
    ),
    "enable_s3_website_endpoint": app.node.try_get_context(
        "enable_s3_website_endpoint"
    ),
    "origin_custom_header_parameter_name": app.node.try_get_context(
        "origin_custom_header_parameter_name"
    ),
    "hosted_zone_id": app.node.try_get_context("hosted_zone_id"),
    "hosted_zone_name": app.node.try_get_context("hosted_zone_name"),
}

StaticSite = StaticSiteStack(
    scope=app,
    construct_id="dev-mermaid-public-site",
    props=props,
    env=cdk_env,
    description="MERMAID dev public file site",
)


app.synth()
