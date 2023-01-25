# CDK

This directory contains the IAC for the mermaid-api using the AWS CDK.

> All deployments are to be done through Github Actions using a branch/tag naming strategy. ie: PRs merged to `dev` will trigger a cdk deploy and `vX.X.X` tags will trigger deploys to prod. Similar to what we're doing today in CircleCI.

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

## Diff

You can run a `cdk diff` from this directory and see the changes that will be applied.

## Deployment

This should be handled through the CI/CD configuration.

## Gotcha's

- There is a Postgres username called `project_admins_reader` that needs to be manually created after RDS is deployed. I had to manually create an EC2 bastion host and set it up so I could talk to RDS and add the user role. This had to be done prior to running a `dbrestore`. I'm not sure why this user/role is not part of the SQL dump?
- When first launching an environment, you have to manually run a `dbrestore` on the corresponding environment. This can be achived by manually running a `ScheduledBackupTask` Task Definition and modifying the command (CMD) to run `dbrestore` instead of `dbbackup`. Once run, the DB will be available and the API will start working. Until that happens, you will see the Fargate service continually try to spin up the API task.
