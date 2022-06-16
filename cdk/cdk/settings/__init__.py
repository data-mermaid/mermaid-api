from cdk.settings.dev import DEV_SETTINGS
from cdk.settings.prod import PROD_SETTINGS
from cdk.settings.settings import ProjectSettings, get_branch_name

if get_branch_name() == "main":
    PROJECT_SETTINGS = PROD_SETTINGS
else:
    PROJECT_SETTINGS = DEV_SETTINGS
