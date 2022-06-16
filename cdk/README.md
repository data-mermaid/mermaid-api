# CDK

This directory contains the IAC for the mermaid-api using the AWS CDK.

> All deployments are to be done through CircleCI (Maybe Github Actions).

## Local Setup

The AWS CDK is a NodeJS cli. So it needs to be installed using `npm install aws-cdk@<version>` (or install it globally with `-g`, users choice). The version should match what is in the `cdk/requirements.txt`.

For the python packages, there is a `cdk/requirements.txt`, so from this directory run `pip install -r requirements.txt` (assuming your venv is active).

## Settings

Each deployment environment is configured using a settings dataclass located in `cdk/settings/`. See `cdk/settings/dev.py` and `cdk/settings/prod.py` for examples.

The default behaviour for switching between environments can be found in `cdk/settings/__init__.py`, and works as follows:

- If the branch name is `main`, then us the production environment settings
- If the branch name is NOT `main`, then use the development environment settings.

## Deployment

Whether a deployment is performed is done through the CICD configuration.

Each deployment will be prefixed with the branch name.
