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

## cdk-nag

[cdk-nag](https://github.com/cdklabs/cdk-nag) runs `AwsSolutionsChecks` during every `cdk synth`. It validates all stacks against the [AWS Solutions](https://github.com/cdklabs/cdk-nag/blob/main/RULES.md#awssolutions) rule pack and **fails synthesis if there are unsuppressed errors**.

### How it works

1. `app.py` attaches the `AwsSolutionsChecks` aspect to the CDK app.
2. During `cdk synth`, cdk-nag inspects every resource and reports errors/warnings.
3. `nag_suppressions.py` contains **resource-scoped** suppressions for findings that have been triaged — each one targets a specific construct path so new resources are never silently covered.
4. The PR workflow (`pr.yml`) runs `cdk synth`, posts the results as a PR comment, and fails the check if any unsuppressed errors exist.

### Adding a suppression

When cdk-nag flags a new resource:

1. Decide whether the finding should be **fixed** (change infra code) or **suppressed** (accepted risk / future TODO).
2. If suppressing, add an entry in `nag_suppressions.py` using `_suppress_by_path()` with the construct path from the error message.
3. Tag the reason with `ACCEPTED` (intentional) or `TODO` (to be addressed later).
4. Run `cdk synth` locally to confirm the error is resolved.

### Running locally

```bash
cd iac && cdk synth --quiet 2>&1 | grep '^\[Error'
```

No output means all findings are suppressed.

## Gotcha's

- There is a Postgres username called `project_admins_reader` that needs to be manually created after RDS is deployed. I had to manually create an EC2 bastion host and set it up so I could talk to RDS and add the user role. This had to be done prior to running a `dbrestore`. I'm not sure why this user/role is not part of the SQL dump?
- When first launching an environment, you have to manually run a `dbrestore` on the corresponding environment. This can be achived by manually running a `ScheduledBackupTask` Task Definition and modifying the command (CMD) to run `dbrestore` instead of `dbbackup`. Once run, the DB will be available and the API will start working. Until that happens, you will see the Fargate service continually try to spin up the API task.
