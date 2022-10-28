"""Settings for development environments"""
from iac.settings.settings import DatabaseSettings, ProjectSettings, DjangoSettings

DEV_ENV_ID = "dev"
DEV_SETTINGS = ProjectSettings(
    
    env_id=DEV_ENV_ID,
    database=DatabaseSettings(name=f"mermaid_{DEV_ENV_ID}", port="5432"),
    api=DjangoSettings(
        container_cpu=512,
        container_memory=1024,
        container_count=1,
        default_domain_api="dev.api2.datamermaid.org",
        default_domain_collect="dev-collect.datamermaid.org",
        mermaid_api_audience="https://dev-api.datamermaid.org",
        
        # Secrets
        dev_emails_name="dev/mermaid-api/dev-emails-mUnSDl"

    ),
)
