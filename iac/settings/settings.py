"""
Settings Class
"""

from dataclasses import dataclass


@dataclass
class DatabaseSettings:
    """Settings Class for Postgres Database"""

    name: str
    port: str


@dataclass
class DjangoSettings:
    """Settings Class for Django API
    Fargate CPU and Memory values
    CPU value	   | Memory value (MiB)
    256 (.25 vCPU) | 512 (0.5GB), 1024 (1GB), 2048 (2GB)
    512 (.5 vCPU)  | 1024 (1GB), 2048 (2GB), 3072 (3GB), 4096 (4GB)
    1024 (1 vCPU)  | 2048 (2GB), 3072 (3GB), 4096 (4GB), 5120 (5GB), 6144 (6GB), 7168 (7GB), 8192 (8GB)
    2048 (2 vCPU)  | Between 4096 (4GB) and 16384 (16GB) in increments of 1024 (1GB)
    4096 (4 vCPU)  | Between 8192 (8GB) and 30720 (30GB) in increments of 1024 (1GB)
    """

    # Dynamic Attrs
    container_cpu: int
    container_memory: int
    container_count: int

    sqs_cpu: int
    sqs_memory: int

    backup_cpu: int
    backup_memory: int

    summary_cpu: int
    summary_memory: int

    default_domain_api: str
    default_domain_collect: str
    mermaid_api_audience: str
    public_bucket: str
    sqs_message_visibility: int

    ic_bucket_name: str

    # Secrets
    env_secret_name: str

    # Common Attrs (defaults)
    # Outlasts invoke_pyspacer's worst case: 2 attempts * (660s read + 10s connect
    # timeout) + one backoff sleep of at most 1s ~= 1341s. Passed to the container
    # as INFERENCE_JOB_VISIBILITY_TIMEOUT (src/app/settings.py), the per-job extension.
    image_sqs_message_visibility: int = 1500
    maintenance_mode: str = "False"
    auth0_management_api_audience: str = "https://datamermaid.auth0.com/api/v2/"
    email_host: str = "smtp.gmail.com"
    email_port: str = "587"
    mc_user: str = "Mermaid"
    # Mirrors IMAGE_S3_PATH in src/app/settings.py: the key prefix under
    # ic_bucket_name that the API stores patch images beneath.
    ic_s3_path: str = "mermaid/"
    ic_bucket_name_test: str = ""
    ic_s3_path_test: str = ""
    # AWS Chatbot Slack integration (leave empty to disable)
    # workspace ID: AWS Console → Chatbot → Configured clients → Slack
    # channel ID: right-click channel in Slack → View channel details → bottom of About tab
    slack_workspace_id: str = ""
    slack_channel_id: str = ""


# The image worker is the pyspacer Lambda's only caller. Shared by worker.py
# (ECS max_scaling_capacity) and InferenceSettings.reserved_concurrency below,
# so raising the task ceiling can't silently leave the Lambda's concurrency
# limit behind.
IMAGE_WORKER_MAX_TASKS = 3


@dataclass
class InferenceSettings:
    """Settings for the pyspacer inference Lambdas (compute lane), one per model version.

    images maps each live model version vN to its model-build ECR tag `vN-K`
    (K = serving build). Bump K for a code/lib fix; add an entry for a retrain.
    active_version is the version the API classifies with. Every other field
    applies to each function. Roll forward by editing these and redeploying
    (git-tracked).
    """

    images: dict[str, str]
    active_version: str
    config_bucket: str = "mermaid-config"
    memory_mb: int = 10240
    # The Lambda's own timeout. src/api/utils/inference.py's _LAMBDA_READ_TIMEOUT
    # must exceed this (in seconds) or botocore's client-side timeout fires first.
    timeout_minutes: int = 10
    ephemeral_storage_gb: int = 2
    # A rolling deployment runs the image-worker ECS service at up to 200% of
    # its task count with old tasks still draining, so the concurrent-invoke
    # ceiling is double IMAGE_WORKER_MAX_TASKS, not the steady-state count.
    # Reserved per function, and subtracted from the account's unreserved pool.
    reserved_concurrency: int = 2 * IMAGE_WORKER_MAX_TASKS
    num_threads: int = 6

    def __post_init__(self) -> None:
        if not self.images:
            raise ValueError("images must list at least one model version")
        # build-push.yml tags the image `${MODEL_VERSION}-${BUILD}` and bakes the same
        # MODEL_VERSION in as CLASSIFIER_VERSION, so `vN-K` implies CLASSIFIER_VERSION=vN.
        for version, image_tag in self.images.items():
            tag_version = image_tag.split("-", 1)[0]
            if tag_version != version:
                raise ValueError(
                    f"image_tag {image_tag!r} serves model version {tag_version!r}, "
                    f"but is listed under {version!r}"
                )
        if self.active_version not in self.images:
            raise ValueError(
                f"active_version {self.active_version!r} is not in images "
                f"({sorted(self.images)!r})"
            )


def pyspacer_function_name(env_id: str, version: str) -> str:
    """The pyspacer inference Lambda's function name for one model version.

    Shared by ApiStack (env var value, ARN string, invoke grant) and InferenceStack
    (the function itself, its log group) so the two stacks cannot name it apart.
    Takes only strings, never a stack or construct, so importing this cannot
    reintroduce the ApiStack<->InferenceStack cycle a cross-stack reference would.

    A bucket policy on coral-reef-training (account 557690602013) grants
    s3:PutObject to prod's functions via an ArnLike condition on
    lambda:SourceFunctionArn matching `prod-mermaid-inference-pyspacer*`. That
    policy is owned outside this repo; a name outside the pattern silently loses
    prod's feature-vector write access with no deploy-time error to surface it.
    """
    return f"{env_id}-mermaid-inference-pyspacer-{version}"


# The image the legacy function served before per-version functions; removed with it next release.
LEGACY_PYSPACER_IMAGE_TAG = "v1-2"


def legacy_pyspacer_function_name(env_id: str) -> str:
    """The unsuffixed pyspacer function name that predates per-version functions.

    Exists for one release only, for workers mid-rollout and a rolled-back API,
    and is removed in the next release.
    """
    return f"{env_id}-mermaid-inference-pyspacer"


def alerts_topic_name(env_id: str) -> str:
    """The shared per-env CloudWatch alerts SNS topic's name.

    Shared by ApiStack's MonitoringAlerts construct (which owns the topic and the
    Chatbot config that delivers it to Slack) and InferenceStack (which resolves it
    by ARN to publish alarm actions) so the two stacks cannot name it apart.
    Takes only env_id, never a stack or construct: a construct reference here would
    order ApiStack ahead of InferenceStack, which must deploy first so every function
    the API points at already exists.
    """
    return f"mermaid-{env_id}-alerts"


@dataclass
class ProjectSettings:
    """Settings Class for Project Envs"""

    # Dynamic Attrs
    env_id: str
    database: DatabaseSettings
    api: DjangoSettings
    inference: "InferenceSettings | None" = None
