import json
import os
import subprocess

import boto3

from iac.settings.dev import DEV_SETTINGS
from iac.settings.prod import PROD_ENV_ID, PROD_SETTINGS

# TODO move these to env var so this script is more generic
REQUIRED_ENV_VARS = [
    "DB_USER",
    "DB_PASSWORD",
    "PGPASSWORD",
    # "DRF_RECAPTCHA_SECRET_KEY",
    # "EMAIL_HOST_USER",
    # "EMAIL_HOST_PASSWORD",
    "SECRET_KEY",
    # "MERMAID_API_SIGNING_SECRET",
    # "SPA_ADMIN_CLIENT_ID",
    # "SPA_ADMIN_CLIENT_SECRET",
    # "MERMAID_MANAGEMENT_API_CLIENT_ID",
    # "MERMAID_MANAGEMENT_API_CLIENT_SECRET",
    # "MC_API_KEY",
    # "MC_LIST_ID",
    # "ADMINS",
    # "SUPERUSER",
    # "AUTH0_DOMAIN",
]


if os.environ["ENV"].lower() == PROD_ENV_ID.lower():
    hosted_settings = PROD_SETTINGS
else:
    hosted_settings = DEV_SETTINGS


def load_env():
    for env_var in REQUIRED_ENV_VARS:
        print(env_var)
        env_var_value = get_env_or_secret(env_var)

        if env_var_value:
            os.environ[env_var] = env_var_value


def get_env_or_secret(env_var_name: str):
    if env_var_name in os.environ.keys() and os.environ.get(env_var_name):
        print("Env Var exists")
        return None

    print("Fetch from SecretsManager")

    env_var_name_name = ""
    if not env_var_name.lower().endswith("name"):
        env_var_name_name = env_var_name + "_NAME"
    print(env_var_name_name)

    if hasattr(hosted_settings.api, env_var_name_name.lower()):
        secretsmanager_name = getattr(hosted_settings.api, env_var_name_name.lower())
    elif hasattr(hosted_settings.database, env_var_name_name.lstrip("DB_").lower()):
        secretsmanager_name = getattr(
            hosted_settings.database, env_var_name_name.lstrip("DB_").lower()
        )
    else:
        raise ValueError
    print(secretsmanager_name)

    ssm = boto3.client("secretsmanager", region_name=os.environ.get("AWS_REGION"))

    # Remove random characters from secret name
    secretsmanager_name_parts = secretsmanager_name.split("/")
    secretsmanager_name_parts[-1] = secretsmanager_name_parts[-1].split("-")[0]

    response = ssm.get_secret_value(SecretId="/".join(secretsmanager_name_parts))

    try:
        field = env_var_name.lstrip("DB_").lower()
        return json.loads(response["SecretString"])[field]
    except json.decoder.JSONDecodeError:
        return response["SecretString"]


def lambda_handler(event, context):
    load_env()
    # TODO pass args to this script so it can be used for other django commands
    result = subprocess.run(
        ["python", "manage.py", "exec_job_lambda", "-m", event],
        # stdin=
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        # capture_output=True,
        check=False,
    )
    print(result.stdout.strip(b"\n"))
