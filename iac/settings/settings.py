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


@dataclass
class InferenceSettings:
    """Settings for the pyspacer inference Lambda (compute lane).

    image_tag is the model-build ECR tag `vN-K` (vN = model version, K = serving build).
    Bump K for a code/lib fix, vN for a retrain. Roll forward by editing this value
    and redeploying (git-tracked). classifier_version is the vN the image serves.
    """

    image_tag: str
    classifier_version: str
    config_bucket: str = "mermaid-config"
    memory_mb: int = 10240
    timeout_minutes: int = 10
    ephemeral_storage_gb: int = 2
    reserved_concurrency: int = 20
    num_threads: int = 6

    def __post_init__(self) -> None:
        # build-push.yml tags the image `${MODEL_VERSION}-${BUILD}` and bakes the same
        # MODEL_VERSION in as CLASSIFIER_VERSION, so `vN-K` implies CLASSIFIER_VERSION=vN.
        tag_version = self.image_tag.split("-", 1)[0]
        if tag_version != self.classifier_version:
            raise ValueError(
                f"image_tag {self.image_tag!r} serves model version {tag_version!r}, "
                f"but classifier_version is {self.classifier_version!r}"
            )


@dataclass
class ProjectSettings:
    """Settings Class for Project Envs"""

    # Dynamic Attrs
    env_id: str
    database: DatabaseSettings
    api: DjangoSettings
    inference: "InferenceSettings | None" = None
