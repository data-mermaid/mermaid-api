"""Settings for production environment"""
from iac.settings.settings import DatabaseSettings, ProjectSettings, DjangoSettings

PROD_ENV_ID = "prod"
PROD_SETTINGS = ProjectSettings(
    
    env_id=PROD_ENV_ID,
    database=DatabaseSettings(name=f"mermaid_{PROD_ENV_ID}", port="5432"),
    api=DjangoSettings(
        container_cpu=1024,
        container_memory=2048,
        container_count=1,
        default_domain_api="api.datamermaid.org",
        default_domain_collect="collect.datamermaid.org",
        mermaid_api_audience="https://api.datamermaid.org",
        public_bucket="public.datamermaid.org",
        
        # Secrets
        spa_admin_client_id_name="prod/mermaid-api/spa-admin-client-id-8GJ1mU",
        spa_admin_client_secret_name="prod/mermaid-api/spa-admin-client-secret-5oMItZ",
        mermaid_api_signing_secret_name="prod/mermaid-api/mermaid-api-signing-secret-3625sz",
    ),
)
