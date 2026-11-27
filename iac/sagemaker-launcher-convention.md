# SageMaker launcher convention (cross-repo)

This document is the **contract** for the per-repo SageMaker launcher
scripts in `mermaid-classifier` and `mermaid-segmentation`. Each repo
has its own copies of `scripts/launch_training.py` and
`scripts/launch_processing.py`. They are not shared code, but they all
follow this convention so users can move between repos without
relearning the system.

## Account and region

- Account: `554812291621` (dev)
- Region: `us-east-1`

All resources below live in this account/region.

## Identity Center permission set

Users sign in via SSO to the `SageMaker` Identity Center permission set.
Its inline policy contains exactly these statements (paste verbatim
if missing):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AssumeMermaidSagemakerLauncher",
      "Effect": "Allow",
      "Action": "sts:AssumeRole",
      "Resource": "arn:aws:iam::554812291621:role/dev-mermaid-sagemaker-launcher-role"
    },
    {
      "Sid": "DescribeAllLogGroups",
      "Effect": "Allow",
      "Action": "logs:DescribeLogGroups",
      "Resource": "*"
    },
    {
      "Sid": "ReadSagemakerJobLogs",
      "Effect": "Allow",
      "Action": [
        "logs:DescribeLogStreams",
        "logs:GetLogEvents",
        "logs:FilterLogEvents",
        "logs:StartLiveTail"
      ],
      "Resource": [
        "arn:aws:logs:us-east-1:554812291621:log-group:/aws/sagemaker/*",
        "arn:aws:logs:us-east-1:554812291621:log-group:/aws/sagemaker/*:*"
      ]
    }
  ]
}
```

The `AssumeRole` statement lets users role-chain from SSO into the
launcher role (which holds the actual job-submission permissions). The
CloudWatch statement is needed for the **AWS Console** to display logs
— the console uses the SSO session, not the chained role.

## ~/.aws/config

```ini
[profile wcs-sso]
sso_start_url      = <your-aws-sso-portal>
sso_region         = us-east-1
sso_account_id     = 554812291621
sso_role_name      = SageMaker
region             = us-east-1
output             = json

[profile wcs-launcher]
source_profile     = wcs-sso
role_arn           = arn:aws:iam::554812291621:role/dev-mermaid-sagemaker-launcher-role
region             = us-east-1
duration_seconds   = 28800
```

```bash
aws sso login --profile wcs-sso
export AWS_PROFILE=wcs-launcher
aws sts get-caller-identity   # should end .../dev-mermaid-sagemaker-launcher-role/...
```

## Canonical ARNs

| Resource | ARN |
|---|---|
| Launcher role | `arn:aws:iam::554812291621:role/dev-mermaid-sagemaker-launcher-role` |
| Job execution role | `arn:aws:iam::554812291621:role/dev-sm-execution-role` |
| Studio UI role | `arn:aws:iam::554812291621:role/dev-sm-studio-role` (the domain's default; not used by jobs) |
| Staging bucket | `s3://dev-datamermaid-sm-data` |
| Classifier ECR | `554812291621.dkr.ecr.us-east-1.amazonaws.com/mermaid-classifier-jobs` |
| Segmentation ECR | `554812291621.dkr.ecr.us-east-1.amazonaws.com/mermaid-segmentation-jobs` |
| MLflow App (classifier) | `arn:aws:sagemaker:us-east-1:554812291621:mlflow-app/app-2OMU4VP53ZS2` (pyspacer) |
| MLflow App (segmentation) | `arn:aws:sagemaker:us-east-1:554812291621:mlflow-app/app-EJVJ6AVFDWW2` (mermaidseg) |

## Per-run YAML schema

Every run is described by a YAML file. The launcher validates against
this schema; unknown top-level keys raise. Required fields are marked
with `*`.

```yaml
job:
  name_prefix: <string>*           # e.g. mermaid-features-2605. Used as
                                   # the SageMaker job name prefix.
  image: <string>*                 # `<repo-short-name>:<tag>` (launcher
                                   # expands to the full ECR URI based on
                                   # which repo it lives in), OR a full
                                   # ECR URI to override. The URI must name
                                   # a mermaid-*-jobs repo in this account.
  entrypoint: <path-in-container>* # Script to run, e.g.
                                   # `scripts/build_feature_bucket.py`.
  instance_type: <ml.* string>*
  instance_count: <int>            # default 1 (TrainingJob only — Processing
                                   # always uses 1)
  volume_gb: <int>*
  max_runtime_hours: <int>*
  use_spot: <bool>                 # default false (TrainingJob only)
  env:                             # extra container env vars
    KEY: VALUE
  tags:                            # extra SageMaker tags
    KEY: VALUE

# Optional. Only on launch_processing.py YAMLs.
processing:
  container_args: [<string>, ...]  # ContainerArguments (positional)
  shard:                           # optional fan-out
    items_from: <path>             # path relative to the config dir
    items_column: <string>         # CSV column name; auto-detect if omitted
    workers: <int>
    per_worker_arg: <string>       # e.g. --source-ids (script flag taking
                                   # the comma-separated chunk)

# Optional. Only on launch_training.py YAMLs.
training:
  hyperparameters:                 # SageMaker hyperparameters dict
    KEY: VALUE
  channels:                        # extra input channels beyond `config`
    channel_name:
      s3_uri: s3://...
      input_mode: File|FastFile|Pipe
```

## Launcher-enforced invariants (NOT YAML-overridable)

- `RoleArn` on the job is always `dev-sm-execution-role` (canonical ARN above).
- `OutputDataConfig.S3OutputPath` is always `s3://dev-datamermaid-sm-data/runs/<run-id>/output/`.
- `config` channel uploaded from the local `--config-dir` lands at:
  - `/opt/ml/input/data/config/` for TrainingJob.
  - `/opt/ml/processing/input/config/` for ProcessingJob.
- `run-id` is always `<job.name_prefix>-<UTC-YYYYMMDDTHHMMSSZ>`.
- Region is always `us-east-1`.
- MLflow tracking URI comes from the launcher CLI flag `--mlflow-tracking-uri` and is injected as env `MLFLOW_TRACKING_SERVER`. Not YAML-configurable.

## Launcher CLI shape (identical across repos)

```bash
uv run python scripts/launch_training.py \
    --run-config sagemaker/runs/my-run.yaml \
    --config-dir sagemaker/configs/my-run/ \
    --mlflow-tracking-uri arn:aws:sagemaker:us-east-1:554812291621:mlflow-app/<app-id> \
    [--dry-run]

uv run python scripts/launch_processing.py \
    --run-config sagemaker/runs/my-extraction.yaml \
    --config-dir sagemaker/configs/my-extraction/ \
    [--dry-run] [--no-wait]
```

The launcher must print, at submission time:
1. Run ID
2. Job ARN
3. CloudWatch log URL
4. (training only) MLflow App URL

## ECR tagging convention

Each repo's ECR holds many independently-tagged images. Two project
images may coexist in one repo (e.g. classifier has both a CPU
training image and a GPU feature-extraction image — different
Dockerfiles, same repo, different tag prefixes).

| Tag pattern | Meaning | Who pushes |
|---|---|---|
| `:training-latest` | Latest training-purpose image. CPU-only by convention in mermaid-classifier; GPU in mermaid-segmentation. | Classifier repo: anyone with launcher role. Segmentation repo: the `sagemaker-image` workflow only. |
| `:training-<git sha>` | (mermaid-segmentation-jobs only) Image for one commit of `main`. The tag is immutable. The repo keeps the newest 50 `training-*` images; older ones expire. | The `sagemaker-image` workflow only |
| `:features-latest` | (mermaid-classifier-jobs only) Latest GPU feature-extraction image. | Anyone |
| `:processing-latest` | (mermaid-classifier-jobs only) Latest GPU processing image. | Anyone |
| `:smoke` | (mermaid-classifier-jobs only) Image known to pass the repo's local smoke recipe. Promoted manually. | Anyone |
| `:prod-YYYY-MM-DD` | (mermaid-classifier-jobs only) Pinned production build. Don't overwrite. | Anyone, by convention |
| `:user-<name>-<purpose>-YYYY-MM-DD` | (mermaid-classifier-jobs only) Personal experimental tags. e.g. `:user-greg-eval-2026-05-25`. | The named user |

`mermaid-segmentation-jobs` is tag-immutable, except for `training-latest`.
Only the `sagemaker-image` GitHub Actions workflow in the
mermaid-segmentation repo pushes to it. The launcher role can read this repo
but cannot push to it. The workflow runs from `main` and
assumes the `mermaid-segmentation-image-push-role` OIDC role, which trusts
only the `sagemaker-image` GitHub environment. Each run pushes
`training-<git sha>` and moves `training-latest` to the same image.

The launcher YAML's `job.image` field accepts either a short form
(`<repo>:<tag>`, where `<repo>` is the bare repo name and the launcher
expands the ECR URI for that repo) or a full ECR URI (for cross-repo
overrides). The execution role can pull only from `mermaid-*-jobs` repos in
this account, so a full URI must name one of them. An image in any other
repo or account needs an IAM change to `SagemakerJobRuntimePolicy` first.

### Build/push recipe

This recipe is for `mermaid-classifier-jobs` only. The launcher role cannot
push to `mermaid-segmentation-jobs`. Push to that
repo through the `sagemaker-image` workflow.

```bash
export AWS_PROFILE=wcs-launcher
ACCT=554812291621
REGION=us-east-1
REPO=mermaid-classifier-jobs
TAG=user-$USER-$(date +%Y-%m-%d)    # or whatever convention applies

aws ecr get-login-password --region $REGION \
    | docker login --username AWS --password-stdin \
        $ACCT.dkr.ecr.$REGION.amazonaws.com

docker buildx build --platform linux/amd64 \
    -t $ACCT.dkr.ecr.$REGION.amazonaws.com/$REPO:$TAG \
    -f docker/jobs/<which>.Dockerfile .

docker push $ACCT.dkr.ecr.$REGION.amazonaws.com/$REPO:$TAG
```

## MLflow tracking

- The classifier uses the **pyspacer** MLflow app.
- The segmentation repo uses the **mermaidseg** MLflow app.
- The execution role (`dev-sm-execution-role`) has
  `sagemaker:CallMlflowAppApi` on `mlflow-app/*`, which covers both apps.
  `sagemaker-mlflow:*` is not enough: it only covers the older MLflow
  tracking servers.
- The job also writes artifacts straight to the app's S3 artifact store
  (`ArtifactStoreUri` from `describe-mlflow-app`). The execution role has
  read/write on `mermaid-mlflow` and access to `dev-datamermaid-sm-data`
  (see "Execution role access"), the two stores in use. A new app with
  another store needs a new grant.
- Each repo's docs should embed the relevant app ARN in its example
  `--mlflow-tracking-uri` invocation.

## Execution role access

`dev-sm-execution-role` is the role jobs run as.

- **Staging bucket writes.** On `dev-datamermaid-sm-data`, write is limited
  to two prefixes:
  - `runs/*`: job output, checkpoints, and config.
  - `mlflow/*`: the artifact store of the mermaid-classifier MLflow App,
    which runs as this role.
- **Secrets.** Jobs can read the Secrets Manager secret
  `mermaid-segmentation/hf-token`, a Hugging Face read token. CDK does not
  create it. Create it by hand. The launcher's `HF_TOKEN_SECRET_ID` must
  name it. The role's grant matches `mermaid-segmentation/hf-token-*`,
  because Secrets Manager adds a random suffix to the secret ARN.

## Checklist for new launcher PRs (any repo)

- [ ] `launch_training.py` and/or `launch_processing.py` follow the CLI shape above.
- [ ] Per-run YAML schema matches this doc; unknown top-level keys raise.
- [ ] Launcher-enforced invariants (above) are not YAML-overridable.
- [ ] `--dry-run` prints the planned config without submitting.
- [ ] CloudWatch URL is printed at submission time.
- [ ] (training only) MLflow App URL is printed at submission time.
- [ ] boto3 errors surface cleanly (no swallowed exceptions).
- [ ] Local smoke recipe present (`docker/jobs/local_smoke.sh`).
- [ ] Unit tests cover schema, dry-run, request shape, and (for processing) shard math.
