from aws_cdk import App

from iac.stacks.common import CommonStack
from iac.stacks.api import ApiStack
from iac.settings import PROJECT_SETTINGS

tags = {
    "Owner": "team@mycompany.com",  # TODO: Update email
    "Environment": PROJECT_SETTINGS.env_id,
    "Git Branch": PROJECT_SETTINGS.branch_name,
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
    f"{PROJECT_SETTINGS.branch_name}-mermaid-api-django",
    config=PROJECT_SETTINGS,
    env=PROJECT_SETTINGS.cdk_env,
    tags=tags,
    vpc=common_stack.vpc,
    database=common_stack.database
)


app.synth()
