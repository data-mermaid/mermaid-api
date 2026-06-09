import os

from aws_cdk import App, Aspects, Environment
from cdk_nag import AwsSolutionsChecks
import nag_suppressions
from settings.dev import DEV_SETTINGS
from settings.prod import PROD_SETTINGS
from stacks.api import ApiStack
from stacks.common import CommonStack
from stacks.github_access import GithubAccessStack
from stacks.sagemaker import SagemakerStack
from stacks.static_site import StaticSiteStack
from stacks.cloudtrail import CloudTrailStack
from stacks.guardduty import GuardDutyStack

tags = {
    "Owner": "sysadmin@datamermaid.org",
    # "Environment": PROJECT_SETTINGS.env_id,
    # "Git Branch": PROJECT_SETTINGS.branch_name,
}


app = App()
Aspects.of(app).add(AwsSolutionsChecks(verbose=True))

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
    enable_vpc_flow_logs=os.getenv("ENABLE_VPC_FLOW_LOGS", "true").lower() == "true",
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
    auto_scaling_group=common_stack.auto_scaling_group,
    distribution=dev_static_site_stack.distribution,
    sagemaker_domain_name=f"{DEV_SETTINGS.env_id}-SG-Project",
    use_fifo_queues="False",
    report_s3_creds=common_stack.report_s3_creds,
    cost_alerts_topic=common_stack.cost_alerts_topic,
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
    auto_scaling_group=common_stack.auto_scaling_group,
    distribution=prod_static_site_stack.distribution,
    sagemaker_domain_name=f"{PROD_SETTINGS.env_id}-SG-Project",
    use_fifo_queues="False",
    report_s3_creds=common_stack.report_s3_creds,
    cost_alerts_topic=common_stack.cost_alerts_topic,
)

cloudtrail_stack = CloudTrailStack(
    app,
    "mermaid-cloudtrail",
    env=cdk_env,
    tags={"Env": "Common"},
)

guardduty_stack = GuardDutyStack(
    app,
    f"mermaid-guardduty-{cdk_env.region}",
    env=cdk_env,
    tags={"Env": "Common"},
    s3_buckets=[
        "2310-coralnet-public-sources",
        "amazon-sagemaker-554812291621-us-east-1-b5cebdff17fb",
        "assets.datamermaid.org",
        "collect-turndown.datamermaid.org",
        "config-bucket-554812291621",
        "dashboard2.datamermaid.org",
        "dev-dashboard2.datamermaid.org",
        "dev-datamermaid-sm-data",
        "dev-datamermaid-sm-sources",
        "dev-explore.datamermaid.org",
        "dev-mermaid-cloudtrail-cloudtrailbucket98b0bfe1-qwlw3gr5rvvm",
        "dev-public.datamermaid.org",
        "dev.app2.datamermaid.org",
        "dev.dashboard3.datamermaid.org",
        "explore.datamermaid.org",
        "mermaid-api-v2-backups",
        "mermaid-config",
        "mermaid-data",
        "mermaid-image-processing",
        "mermaid-user-metrics",
        "prod.app2.datamermaid.org",
        "public.datamermaid.org",
        "pyspacer-test",
        "sagemaker-studio-554812291621-moo6nyhibza",
        "sagemaker-us-east-1-554812291621",
        "vpcflowlogs.admin.datamermaid.org",
    ],
)

nag_suppressions.apply_all(
    gh_access_stack=gh_access_stack,
    common_stack=common_stack,
    dev_static_site_stack=dev_static_site_stack,
    prod_static_site_stack=prod_static_site_stack,
    dev_api_stack=dev_api_stack,
    prod_api_stack=prod_api_stack,
    dev_sagemaker_stack=dev_sagemaker_stack,
    cloudtrail_stack=cloudtrail_stack,
    guardduty_stack=guardduty_stack,
)

app.synth()
