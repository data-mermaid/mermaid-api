"""Settings for development environments"""

from settings.settings import DatabaseSettings, DjangoSettings, ProjectSettings

DEV_ENV_ID = "dev"
DEV_SETTINGS = ProjectSettings(
    env_id=DEV_ENV_ID,
    database=DatabaseSettings(name=f"mermaid_{DEV_ENV_ID}", port="5432"),
    api=DjangoSettings(
        # API
        container_cpu=1024,
        container_memory=2048,
        container_count=1,
        # SQS
        sqs_cpu=1024,
        sqs_memory=2048,
        # Backup
        backup_cpu=512,
        backup_memory=1024,
        # Summary
        summary_cpu=1024,
        summary_memory=2048,
        default_domain_api="dev-api.datamermaid.org",
        default_domain_collect="https://dev-app.datamermaid.org",
        mermaid_api_audience="https://dev-api.datamermaid.org",
        public_bucket="dev-public.datamermaid.org",
        sqs_message_visibility=60,
        # Image classification
        ic_bucket_name="mermaid-image-processing",
        # Secrets
        env_secret="dev/mermaid-api-MzD7rS",
    ),
)
