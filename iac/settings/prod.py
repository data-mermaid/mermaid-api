"""Settings for production environment"""

import os

from settings.settings import (
    DatabaseSettings,
    DjangoSettings,
    InferenceSettings,
    ProjectSettings,
)

PROD_ENV_ID = "prod"
PROD_SETTINGS = ProjectSettings(
    env_id=PROD_ENV_ID,
    database=DatabaseSettings(name=f"mermaid_{PROD_ENV_ID}", port="5432"),
    api=DjangoSettings(
        # API
        container_cpu=1500,
        # 3000 MiB spiked to the cap daily (heavy obs/report serialization),
        # OOM-killing gunicorn workers. Headroom above the ~3078 MiB peak.
        container_memory=4096,
        # Was 1. A single task means 8 gthread slots (2 workers x 4 threads) total
        # for all of prod, and a blocking request type (e.g. collectrecords/submit's
        # synchronous per-image S3 PUT loop in create_image_annotations_files) can
        # exhaust them and queue every other request behind it. 2 doubles slots to
        # 16 and removes the single-target-is-the-whole-service failure mode.
        container_count=2,
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
        image_sqs_message_visibility=1500,
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
    inference=InferenceSettings(image_tag="v1-2", classifier_version="v1"),
)
