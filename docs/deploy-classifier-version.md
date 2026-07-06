# Deploying a new classifier version

How to release a new coral-image classifier and cut it over to the production
inference Lambda. This is the **steady-state** procedure for after the API is
fully cut over to the classifier pipeline (mermaid-classifier
[#54](https://github.com/data-mermaid/mermaid-classifier/issues/54)).

Three GitHub Actions, run in order, across three repos:

| # | Repo | Workflow | What it does |
|---|------|----------|--------------|
| 1 | [`mermaid-classifier`](https://github.com/data-mermaid/mermaid-classifier) | [Release classifier version](https://github.com/data-mermaid/mermaid-classifier/actions/workflows/release.yml) | Exports the model from MLflow to `s3://mermaid-config/classifier/vN/` and cuts release `vN`. |
| 2 | [`mermaid-inference`](https://github.com/data-mermaid/mermaid-inference) | [Build and push inference image](https://github.com/data-mermaid/mermaid-inference/actions/workflows/build-push.yml) | Builds the Lambda container image and pushes it to ECR as `vN-K`. |
| 3 | [`mermaid-api`](https://github.com/data-mermaid/mermaid-api) (this repo) | [Deploy CDK](https://github.com/data-mermaid/mermaid-api/actions/workflows/deploy-cdk.yml) | Points the inference Lambda at the new image `vN-K`. |

**Versioning:** `vN` is the **model version** — bump it (`v2` → `v3`) for a
retrain. `K` is the **serving build** under a model version — bump it (`v3-1` →
`v3-2`) for a code/library fix that reuses the same model. Both the release tag
and the ECR repo are **immutable**: re-running an existing `vN` or re-pushing an
existing `vN-K` fails, so always move to a fresh number.

---

## Prerequisites

- A trained model registered in MLflow that you want to release.
- The next version numbers decided: a new `vN` for a retrain, or the existing
  `vN` with the next `K` for a code/library fix.
- Permission to run `workflow_dispatch` workflows in all three repos.

## Find the MLflow model ID

Step 1 needs the MLflow **logged-model ID** (an `m-…` string), which is not
surfaced in the MERMAID API and is awkward to find in the MLflow UI. Resolve it
from the registered **model name + registry version** with the MLflow client.
From a [`mermaid-classifier`](https://github.com/data-mermaid/mermaid-classifier)
checkout (it has MLflow via the `training` extra):

```bash
MLFLOW_TRACKING_URI=<tracking-uri> \
  uv run --extra training python -c \
  "from mlflow import MlflowClient; print(MlflowClient().get_model_version('<model-name>', '<registry-version>').model_id)"
# prints e.g. m-1a2b3c...   <- paste this into the release workflow's mlflow_model_id
```

`<registry-version>` is the integer version in the MLflow model registry (e.g.
`3`) — this is **not** the same as the release `vN` you choose in step 1.

---

## Step 1 — Release the classifier artifact

Run **[Release classifier version](https://github.com/data-mermaid/mermaid-classifier/actions/workflows/release.yml)**
in `mermaid-classifier` (`workflow_dispatch`) with:

| Input | Value |
|-------|-------|
| `mlflow_model_id` | the `m-…` ID from above |
| `version` | the release tag, e.g. `v3` |

It exports and re-validates `model.pt` + `model.json`, pushes them to
`s3://mermaid-config/classifier/vN/`, and cuts GitHub release **`vN`**. The
MLflow tracking URI and AWS role are preconfigured repo secrets — no extra
arguments needed.

> Versions are immutable — re-running an existing `vN` fails. See
> [Releasing a classifier version](https://github.com/data-mermaid/mermaid-classifier#releasing-a-classifier-version)
> in the classifier README for details.

## Step 2 — Build and push the inference image

Run **[Build and push inference image](https://github.com/data-mermaid/mermaid-inference/actions/workflows/build-push.yml)**
in `mermaid-inference` (`workflow_dispatch`) with:

| Input | Value |
|-------|-------|
| `model_version` | the same `vN` from step 1, e.g. `v3` |
| `build` | the serving build number `K`, starting at `1` |
| `classifier_ref` | the `mermaid-classifier` git tag from step 1, e.g. `v3` |

It builds the `pyspacer-function` Lambda image (baking in
`CLASSIFIER_VERSION=vN` and pinning the matching pyspacer/sklearn) and pushes it
to the ECR repo `mermaid-inference-pyspacer` tagged **`vN-K`**.

## Step 3 — Point the Lambda at the new image

The Lambda's image tag is pinned in this repo's CDK config — building the image
in step 2 does **not** by itself update the running Lambda. Bump the tag and
deploy:

1. Edit [`iac/settings/dev.py`](../iac/settings/dev.py) and set the inference
   image tag to the `vN-K` from step 2:

   ```python
   inference=InferenceSettings(image_tag="v3-2"),
   ```

2. Commit the change to `dev` (via PR).
3. Run **[Deploy CDK](https://github.com/data-mermaid/mermaid-api/actions/workflows/deploy-cdk.yml)**.
   Deploying `InferenceStack` updates `PyspacerInferenceFunction` to serve the
   new image. Git history of `dev.py` is the deploy log.

Once the deploy completes, the inference Lambda serves the new classifier
version.
