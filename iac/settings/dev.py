"""Settings for development environments"""
from settings.settings import DatabaseSettings, DjangoSettings, ProjectSettings

DEV_ENV_ID = "dev"
DEV_SETTINGS = ProjectSettings(
    env_id=DEV_ENV_ID,
    database=DatabaseSettings(name=f"mermaid_{DEV_ENV_ID}", port="5432"),
    api=DjangoSettings(
        # API
        container_cpu=512,
        container_memory=1024,
        container_count=1,
        # SQS
        sqs_cpu=512,
        sqs_memory=1024,
        # Backup
        backup_cpu=512,
        backup_memory=1024,
        default_domain_api="dev-api.datamermaid.org",
        default_domain_collect="https://dev-app.datamermaid.org",
        mermaid_api_audience="https://dev-api.datamermaid.org",
        public_bucket="dev-public.datamermaid.org",
        sqs_message_visibility=3000,
        # Secrets
        dev_emails_name="dev/mermaid-api/dev-emails-mUnSDl",
        spa_admin_client_id_name="common/mermaid-api/spa-admin-client-id-FuMVtc",
        spa_admin_client_secret_name="common/mermaid-api/spa-admin-client-secret-kYccw0",
        mermaid_api_signing_secret_name="common/mermaid-api/mermaid-api-signing-secret-FM7ATI",
        mermaid_management_api_client_id_name="common/mermaid-api/mermaid-management-api-client-id-nIWaxV",
        mermaid_management_api_client_secret_name="common/mermaid-api/mermaid-management-api-client-secret-HNVoT0",
    ),
)
