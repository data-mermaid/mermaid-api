# CDK

This directory contains the IAC for the mermaid-api using the AWS CDK.

> All deployments are to be done through Github Actions using a branch naming strategy. ie: PRs merged to dev/develop will trigger a cdk deploy and tags will trigger deploys to prod. Similar to what we're doing today in CircleCI.

## Local Setup 

Note: This is for running `cdk synth` and `cdk diff` commands. Do NOT run `cdk deploy` commands locally. Allow this to be handled by the CD in Github Actions

### Prerequisites

- Node
- Pip

### Installation

Activate your virtual environment and run the following script to install the CDK CLI and it's python libraries: 
- `./install_cdk.sh`

## Settings

Each deployment environment is configured using a settings dataclass located in `iac/settings/`. See `iac/settings/dev.py` and `iac/settings/prod.py` for examples.

The default behaviour for switching between environments can be found in `iac/settings/__init__.py`, and works as follows:

- If the branch name is `main`, then use the production environment settings
- If the branch name is NOT `main`, then use the development environment settings.

## Diff

You can run a `cdk diff` from this directory and see the changes that will be applied.

## Deployment

This should be handled through the CI/CD configuration.
