# Deploying a new classifier version

How to release a new coral-image classifier and cut the API over to it through
its own per-version inference Lambda. This is the **steady-state** procedure for after the API is
fully cut over to the classifier pipeline (mermaid-classifier
[#54](https://github.com/data-mermaid/mermaid-classifier/issues/54)).

Three GitHub Actions, run in order, across three repos:

| # | Repo | Workflow | What it does |
|---|------|----------|--------------|
| 1 | [`mermaid-classifier`](https://github.com/data-mermaid/mermaid-classifier) | [Release classifier version](https://github.com/data-mermaid/mermaid-classifier/actions/workflows/release.yml) | Exports the model from MLflow to `s3://mermaid-config/classifier/vN/` and cuts release `vN`. |
| 2 | [`mermaid-inference`](https://github.com/data-mermaid/mermaid-inference) | [Build and push inference image](https://github.com/data-mermaid/mermaid-inference/actions/workflows/build-push.yml) | Builds the Lambda container image and pushes it to ECR as `vN-K`. |
| 3 | [`mermaid-api`](https://github.com/data-mermaid/mermaid-api) (this repo) | [Deploy CDK](https://github.com/data-mermaid/mermaid-api/actions/workflows/deploy-cdk.yml) | Adds a per-version inference Lambda for the new image `vN-K` and points the API at it. |

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
- For prod, the foreign `coral-reef-training` bucket's policy must allow the
  new version's function to write feature vectors. The AWS Open Data account
  (557690602013) owns that policy. It must allow `lambda:SourceFunctionArn`
  with an `ArnLike` condition on
  `arn:aws:lambda:us-east-1:<account>:function:prod-mermaid-inference-pyspacer*`.
  Without it, the new version's feature-vector writes fail with AccessDenied
  and the `mermaid-prod-inference-<version>-feature-store-errors` alarm fires.

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

## Step 3 — Validate the manifest (recommended)

`Classifier.active()` (`src/api/models/classification.py`) looks up the
`Classifier` row for `INFERENCE_CLASSIFIER_VERSION` by exact match. You do not
create that row by hand: when an image worker starts in dev or prod, it
registers every live version (each key of `INFERENCE_PYSPACER_FUNCTIONS`) from
`classifier/<version>/model.json` if no row exists yet
(`ensure_live_classifiers_registered` in `src/api/checks.py`). An existing row
is left untouched.

If registration fails (the manifest is missing or malformed, or a label does
not resolve to a benthic attribute or growth form), the image worker exits
before taking jobs. The ECS circuit breaker then rolls back the image worker,
and the `*-mermaid-api-django` deploy fails. The API rolls back to the previous
`active_version`, whose function still exists unchanged, so classification
keeps working. The new version's function is already deployed but unused until
the manifest is fixed and the change redeployed.

To catch this before the deploy, dry-run the registration in each environment
before editing `active_version`:

```bash
python manage.py register_classifier vN --dry-run
```

Running it without `--dry-run` registers the row ahead of the deploy, which is
also safe: `Classifier.active()` ignores rows the pin does not point at, and
the worker then finds the row and skips S3. Run it without `--dry-run` again
to re-apply a corrected `model.json` to an existing row. The worker never
re-applies one.

> **This only works for a version whose S3 prefix has a `model.json`.**
> `Classifier.register()` reads `classifier/<version>/model.json`, and the
> Beta version `v1` has none — it predates this manifest and uses the legacy
> pickle layout instead, so `register_classifier v1` fails by design. `v1`'s
> row exists only because it was created by hand, so the worker's startup
> check passes on it without reading S3. On a database without that row,
> keeping `v1` live fails the deploy; restore the row from a backup. See
> [mermaid-classifier#102](https://github.com/data-mermaid/mermaid-classifier/issues/102),
> which tracks the gap.

## Step 4 — Point the API at the new image

Each live model version has its own Lambda, `{env}-mermaid-inference-pyspacer-{version}`
(construct `Pyspacer-{version}`), deployed from the image tag listed for it in
this repo's CDK config **per environment** (`InferenceSettings.images`).
Building the image in step 2 does **not** by itself deploy anything. Edit both
environments' settings files in one PR, then let the normal release flow roll
it out: dev first, prod after validating on dev. `active_version` also feeds
`INFERENCE_CLASSIFIER_VERSION` on the API service and both workers (`ApiStack`),
and `images` feeds `INFERENCE_PYSPACER_FUNCTIONS` (version to function name),
so the change redeploys `dev-mermaid-api-django` / `prod-mermaid-api-django`
(new task definition revisions) alongside `dev-mermaid-inference` /
`prod-mermaid-inference` — expect both stacks in the same deploy.

A new version deploys as an additional function; the previous version's
function is not touched. A `K` bump changes one entry's tag and updates only
that version's function in place. Each function has its own alarms:
`mermaid-{env}-inference-{version}-errors`, `-throttles`, `-processing-errors`
and `-feature-store-errors`.

> For this release only, the unsuffixed `{env}-mermaid-inference-pyspacer`
> function is still deployed. The code pins it to the literal image tag `v1-2`
> (`LEGACY_PYSPACER_IMAGE_TAG` in `iac/settings/settings.py`), so it stays
> unchanged even if `active_version` changes. The next release removes it.

> One caveat remains: `classify_image_job` does not send a version yet, so a
> job queued before the cut-over runs on whichever version is active when a
> worker picks it up. A job that names a version no longer in the function map
> falls back to the active version with a warning. Per-job version pinning
> arrives in the next release.

1. **Edit both settings files.** In one PR, make the same edit to
   [`iac/settings/dev.py`](../iac/settings/dev.py) and
   [`iac/settings/prod.py`](../iac/settings/prod.py): add `"vN": "vN-K"` (the
   tag from step 2) to `images`, set `active_version` to the new `vN`, and
   **keep the previous version's entry**:

   ```python
   inference=InferenceSettings(images={"v1": "v1-2", "v2": "v2-1"}, active_version="v2"),
   ```

   `cdk synth` asserts that each tag's `vN` matches its key in `images` and
   that `active_version` is a key of `images`, since a CI-built image always
   pairs them this way.

2. **Deploy and test on dev.** Merge the PR to `dev`. This triggers
   **[Deploy CDK](https://github.com/data-mermaid/mermaid-api/actions/workflows/deploy-cdk.yml)**,
   which deploys `dev-mermaid-inference-pyspacer-vN` from the new image, and
   rolls `dev-mermaid-api-django`'s API/worker tasks to the matching
   `INFERENCE_CLASSIFIER_VERSION`. Validate on dev before going on.
   The `prod.py` edit has no effect yet: dev pushes deploy only the dev stacks.

3. **Deploy to prod.** Merge `dev` to `master` and cut a release tag
   (e.g. `v1.2`). The tag push triggers the **Deploy CDK** prod job, which
   updates `prod-mermaid-inference` and `prod-mermaid-api-django` the same way.

Git history of `dev.py` / `prod.py` is the deploy log. Once the prod deploy
completes, the API classifies with the new classifier version.

## Retiring a version

Remove an old version's entry from `images` in `dev.py` and `prod.py` in a
later PR, once both hold:

- the new version has been `active_version` in prod, and
- the image queue and its dead-letter queue hold no jobs from before the
  cut-over.

Removing the entry deletes that version's function, log group and alarms.

Never remove a version's entry in the same deploy that stops the API from
using it. Remove it in a later deploy, after the API and worker rollout has
finished.

## Rolling back the per-version release

To revert the release that introduced per-version functions, use **two
deploys**, never one:

1. **Restore the API, keep the functions.** Restore the previous API code and
   environment, but keep the `images` entries so the
   `{env}-mermaid-inference-pyspacer-vN` functions stay deployed.
2. **Remove the functions.** After the API and worker rollout from the first
   deploy has finished, remove them.

`*-mermaid-inference` deploys before `*-mermaid-api-django`
(`.github/workflows/deploy-cdk.yml`). A one-step revert deletes the versioned
functions while workers still on the new code are invoking them. Lambda then
returns `ResourceNotFoundException`, which the API treats as non-retryable, so
images uploaded in that window are marked FAILED and are not retried.
