"""Settings for production environment"""
from settings.settings import DatabaseSettings, DjangoSettings, ProjectSettings

PROD_ENV_ID = "prod"
PROD_SETTINGS = ProjectSettings(
    env_id=PROD_ENV_ID,
    database=DatabaseSettings(name=f"mermaid_{PROD_ENV_ID}", port="5432"),
    api=DjangoSettings(
        # API
        container_cpu=1024,
        container_memory=2048,
        container_count=1,
        # SQS
        sqs_cpu=800,
        sqs_memory=2048,
        # Backup
        backup_cpu=1024,
        backup_memory=2048,
        default_domain_api="api.datamermaid.org",
        default_domain_collect="https://app.datamermaid.org",
        mermaid_api_audience="https://api.datamermaid.org",
        public_bucket="public.datamermaid.org",
        sqs_message_visibility=3000,
        # Secrets
        spa_admin_client_id_name="prod/mermaid-api/spa-admin-client-id-8GJ1mU",
        spa_admin_client_secret_name="prod/mermaid-api/spa-admin-client-secret-5oMItZ",
        mermaid_api_signing_secret_name="prod/mermaid-api/mermaid-api-signing-secret-3625sz",
        mermaid_management_api_client_id_name="prod/mermaid-api/mermaid-management-api-client-id-Kb3Sty",
        mermaid_management_api_client_secret_name="prod/mermaid-api/mermaid-management-api-client-secret-HHVBL1",
    ),
)
