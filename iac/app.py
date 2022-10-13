from aws_cdk import App

from iac.stacks.common import CommonStack
from iac.stacks.api import ApiStack
from iac.settings import PROJECT_SETTINGS

tags = {
    "Owner": "sysadmin@datamermaid.org",
    # "Environment": PROJECT_SETTINGS.env_id,
    # "Git Branch": PROJECT_SETTINGS.branch_name,
}


app = App()


common_stack = CommonStack(
    app,
    f"mermaid-api-infra-common",
    config=PROJECT_SETTINGS,
    env=PROJECT_SETTINGS.cdk_env,
    tags=tags,
)

api_stack = ApiStack(
    app,
    f"{PROJECT_SETTINGS.env_id}-mermaid-api-django",
    config=PROJECT_SETTINGS,
    env=PROJECT_SETTINGS.cdk_env,
    tags=tags,
    cluster=common_stack.cluster,
    database=common_stack.database,
    backup_bucket=common_stack.backup_bucket,
    load_balancer=common_stack.load_balancer,
    container_security_group=common_stack.ecs_sg,
)


app.synth()
