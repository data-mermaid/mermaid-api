"""Settings for production environment"""

from settings.settings import DatabaseSettings, DjangoSettings, ProjectSettings
import os

PROD_ENV_ID = "prod"
PROD_SETTINGS = ProjectSettings(
    env_id=PROD_ENV_ID,
    database=DatabaseSettings(name=f"mermaid_{PROD_ENV_ID}", port="5432"),
    api=DjangoSettings(
        # API
        container_cpu=1500,
        container_memory=3000,
        container_count=1,
        # SQS
        sqs_cpu=2048,
        sqs_memory=4096,
        # Backup
        backup_cpu=1024,
        backup_memory=2048,
        # Summary
        summary_cpu=1024,
        summary_memory=4096,
        default_domain_api="api.datamermaid.org",
        default_domain_collect="https://app.datamermaid.org",
        mermaid_api_audience="https://api.datamermaid.org",
        public_bucket="public.datamermaid.org",
        sqs_message_visibility=60,
        # Image classification
        ic_bucket_name="coral-reef-training",
        ic_bucket_name_test="mermaid-image-processing",
        ic_s3_path_test="mermaid-production-test/",
        # Secrets
        env_secret_name="prod/mermaid-api-GUqRBj",
        # Slack alerts via AWS Chatbot — fill in after connecting workspace in console
        slack_workspace_id=os.getenv("SLACK_WORKSPACE_ID", ""),
        slack_channel_id=os.getenv("SLACK_CHANNEL_ID", ""),
    ),
)
