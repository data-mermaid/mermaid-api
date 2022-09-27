from iac.settings.dev import DEV_SETTINGS

# from iac.settings.prod import PROD_SETTINGS
from iac.settings.settings import ProjectSettings
from iac.settings.utils import get_branch_name

if get_branch_name() == "main":
    raise NotImplementedError("Prod config is not ready!")
else:
    PROJECT_SETTINGS = DEV_SETTINGS
