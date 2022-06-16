from aws_cdk import App

from cdk.main import MainStack
from cdk.settings import PROJECT_SETTINGS

tags = {
    "Owner": "team@mycompany.com",  # TODO: Update email
    "Environment": PROJECT_SETTINGS.env_id,
    "Git Branch": PROJECT_SETTINGS.branch_name,
}


app = App()


main_stack = MainStack(
    app,
    f"{PROJECT_SETTINGS.branch_name}-main",
    config=PROJECT_SETTINGS,
    env=PROJECT_SETTINGS.cdk_env,
    tags=tags,
)


app.synth()
