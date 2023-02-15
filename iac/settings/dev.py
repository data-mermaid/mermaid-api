"""Settings for development environments"""
from iac.settings.settings import DatabaseSettings, ProjectSettings, DjangoSettings

DEV_ENV_ID = "dev"
DEV_SETTINGS = ProjectSettings(
    
    env_id=DEV_ENV_ID,
    database=DatabaseSettings(name=f"mermaid_{DEV_ENV_ID}", port="5432"),
    api=DjangoSettings(
        container_cpu=1024,
        container_memory=2048,
        container_count=1,
        default_domain_api="dev-api.datamermaid.org",
        default_domain_collect="dev-collect.datamermaid.org",
        mermaid_api_audience="https://dev-api.datamermaid.org",
        public_bucket="dev-public.datamermaid.org",
        sqs_message_visibility=600,
        
        # Secrets
        dev_emails_name="dev/mermaid-api/dev-emails-mUnSDl",
        spa_admin_client_id_name="common/mermaid-api/spa-admin-client-id-FuMVtc",
        spa_admin_client_secret_name="common/mermaid-api/spa-admin-client-secret-kYccw0",
        mermaid_api_signing_secret_name="common/mermaid-api/mermaid-api-signing-secret-FM7ATI",
    ),
)
