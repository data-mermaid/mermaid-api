import os
import sys

import boto3
import requests
from corsheaders.defaults import default_methods

# Options: None, DEV, PROD
ENVIRONMENT = os.environ.get("ENV") or "local"
if ENVIRONMENT:
    ENVIRONMENT = ENVIRONMENT.lower()
PROJECT_NAME = "MERMAID API"

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    with open(os.path.join(BASE_DIR, "VERSION.txt")) as f:
        API_VERSION = f.read().replace("\n", "")
except Exception as _:
    API_VERSION = "NA"

LOGIN_REDIRECT_URL = "api-root"
SECRET_KEY = os.environ.get("SECRET_KEY")

# Set to True to prevent db writes and return 503
MAINTENANCE_MODE = os.environ.get("MAINTENANCE_MODE") == "True" or False
MAINTENANCE_MODE_IGNORE_ADMIN_SITE = os.environ.get("MAINTENANCE_MODE_IGNORE_ADMIN_SITE", True)
MAINTENANCE_MODE_IGNORE_STAFF = os.environ.get("MAINTENANCE_MODE_IGNORE_STAFF", True)
MAINTENANCE_MODE_IGNORE_SUPERUSER = os.environ.get("MAINTENANCE_MODE_IGNORE_SUPERUSER", True)
# the absolute url where users will be redirected to during maintenance-mode
# MAINTENANCE_MODE_REDIRECT_URL = 'https://datamermaid.org/'
# Other maintenance_mode settings: https://github.com/fabiocaccamo/django-maintenance-mode

_admins = os.environ.get("ADMINS") or ""
ADMINS = [("Datamermaid admin", admin.strip()) for admin in _admins.split(",")]
SUPERUSER = ("Datamermaid superuser", os.environ.get("SUPERUSER"))
DEFAULT_DOMAIN_MARKETING = os.environ.get("DEFAULT_DOMAIN_MARKETING", "https://datamermaid.org")
DEFAULT_DOMAIN_API = os.environ.get("DEFAULT_DOMAIN_API")
DEFAULT_DOMAIN_COLLECT = os.environ.get("DEFAULT_DOMAIN_COLLECT")
DEFAULT_DOMAIN_DASHBOARD = os.environ.get(
    "DEFAULT_DOMAIN_DASHBOARD", "https://explore.datamermaid.org"
)

# Application definition

INSTALLED_APPS = [
    "corsheaders",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "django.contrib.gis",
    "maintenance_mode",
    "rest_framework",
    "rest_framework_gis",
    "django_filters",
    "django_extensions",
    "drf_recaptcha",
    "nested_admin",
    "api.apps.ApiConfig",
    "tools",
    "taggit",
    "simpleq",
    "sqltables",
]

MIDDLEWARE = [
    "api.middleware.HealthEndpointMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "maintenance_mode.middleware.MaintenanceModeMiddleware",
    "api.middleware.APIVersionMiddleware",
    "api.middleware.MetricsMiddleware",
]

DEBUG = False
TESTING = False
DEBUG_LEVEL = "ERROR"
CONN_MAX_AGE = 0
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_METHODS = list(default_methods) + ["HEAD"]
CORS_EXPOSE_HEADERS = ["HTTP_API_VERSION"]
# https://github.com/adamchainz/django-cors-headers#cors_allow_credentials-bool
CORS_ALLOW_CREDENTIALS = True

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
_dev_emails = os.environ.get("DEV_EMAILS") or ""
DEV_EMAILS = [email.strip() for email in _dev_emails.split(",")]

_allowed_hosts = os.environ.get("ALLOWED_HOSTS") or ""
ALLOWED_HOSTS = [host.strip() for host in _allowed_hosts.split(",")]

# Look for Fargate IP, for health checks.
METADATA_URI = os.getenv("ECS_CONTAINER_METADATA_URI", None)
IN_ECS = METADATA_URI is not None

if IN_ECS:
    container_metadata = requests.get(METADATA_URI).json()
    # allow container IPs for ALB health checks
    ALLOWED_HOSTS.append(container_metadata["Networks"][0]["IPv4Addresses"][0])
    ALLOWED_HOSTS.append(".datamermaid.org")

if ENVIRONMENT not in ("dev", "prod"):
    DEBUG_LEVEL = "DEBUG"
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
    ALLOWED_HOSTS = ["*"]
    DEBUG = True
    MEDIA_ROOT = os.path.join(BASE_DIR, "media")
    MEDIA_URL = "/media/"

# SSL settings
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

ROOT_URLCONF = "app.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]
REPORT_TEMPLATES = [
    os.path.join(BASE_DIR, "api", "reports", "templates"),
]

WSGI_APPLICATION = "app.wsgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "api.auth_backends.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticatedOrReadOnly",),
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "DEFAULT_RENDERER_CLASSES": (
        # 'api.renderers.BaseBrowsableAPIRenderer',
        "rest_framework.renderers.JSONRenderer",
    ),
    "COERCE_DECIMAL_TO_STRING": False,
    "DEFAULT_SCHEMA_CLASS": "rest_framework.schemas.openapi.AutoSchema",
}

DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": os.environ.get("DB_NAME") or "mermaid",
        "USER": os.environ.get("DB_USER") or "postgres",
        "PASSWORD": os.environ.get("DB_PASSWORD") or "postgres",
        "HOST": os.environ.get("DB_HOST") or "localhost",
        "PORT": os.environ.get("DB_PORT") or "5432",
        "TEST": {
            "NAME": "test_mermaid",  # explicitly setting default
        },
    }
}

# Password validation
# https://docs.djangoproject.com/en/1.10/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
# https://docs.djangoproject.com/en/1.10/topics/i18n/

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.10/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "static")

# *****************
# **    Auth0    **
# *****************

AUTH0_DOMAIN = os.environ.get("AUTH0_DOMAIN")
AUTH0_USER_INFO_ENDPOINT = "https://{domain}/userinfo".format(domain=AUTH0_DOMAIN)
AUTH0_MANAGEMENT_API_AUDIENCE = os.environ.get("AUTH0_MANAGEMENT_API_AUDIENCE")
MERMAID_API_AUDIENCE = os.environ.get("MERMAID_API_AUDIENCE")
MERMAID_API_SIGNING_SECRET = os.environ.get("MERMAID_API_SIGNING_SECRET")

# *********
# ** API **
# *********

AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.environ.get("AWS_REGION") or "us-east-1"
S3_DBBACKUP_MAXAGE = 60  # days

EMAIL_HOST = os.environ.get("EMAIL_HOST")
EMAIL_PORT = os.environ.get("EMAIL_PORT")
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = "MERMAID System <{}>".format(EMAIL_HOST_USER)
WEBCONTACT_EMAIL = f"MERMAID Web Contact <{os.environ.get('WEBCONTACT_EMAIL')}>"

API_NULLQUERY = "null"
TAGGIT_CASE_INSENSITIVE = True
GEO_PRECISION = 6  # to nearest 10 cm
CORAL_ATLAS_APP_ID = os.environ.get("CORAL_ATLAS_APP_ID")
# https://github.com/llybin/drf-recaptcha
DRF_RECAPTCHA_SECRET_KEY = os.environ.get("DRF_RECAPTCHA_SECRET_KEY")
DRF_RECAPTCHA_TESTING = os.environ.get("DRF_RECAPTCHA_TESTING") or False
# DRF_RECAPTCHA_DEFAULT_V3_SCORE = 0.3

# buckets
AWS_CONFIG_BUCKET = "mermaid-config"
AWS_DATA_BUCKET = "mermaid-data"
AWS_BACKUP_BUCKET = os.environ.get("AWS_BACKUP_BUCKET")
AWS_METRICS_BUCKET = "mermaid-user-metrics"
PUBLIC_BUCKET = os.environ.get("AWS_PUBLIC_BUCKET")
IMAGE_PROCESSING_BUCKET = os.environ.get("IMAGE_PROCESSING_BUCKET")

# ************
# ** CLIENT **
# ************

# MERMAID Collect (SPA)
SPA_ADMIN_CLIENT_ID = os.environ.get("SPA_ADMIN_CLIENT_ID")
SPA_ADMIN_CLIENT_SECRET = os.environ.get("SPA_ADMIN_CLIENT_SECRET")

# MERMAID Management API (Non Interactive)
MERMAID_MANAGEMENT_API_CLIENT_ID = os.environ.get("MERMAID_MANAGEMENT_API_CLIENT_ID")
MERMAID_MANAGEMENT_API_CLIENT_SECRET = os.environ.get("MERMAID_MANAGEMENT_API_CLIENT_SECRET")

boto3_client = boto3.client(
    "logs",
    aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
    region_name=AWS_REGION,
)

# MAILCHIMP
MC_API_KEY = os.environ.get("MC_API_KEY")
MC_USER = os.environ.get("MC_USER")
MC_LIST_ID = os.environ.get("MC_LIST_ID")

# ************************
# ** METRICS MIDDLEWARE **
# ************************

DISABLE_METRICS = False
WRITE_METRICS_TO_DB = DEBUG is False
DB_LOGGER_BATCH_WRITE_SIZE = 100
# Uses Python's startswith() to match routes
METRICS_IGNORE_ROUTES = [
    "/v1/health/",
]


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "require_not_maintenance_mode_503": {
            "()": "maintenance_mode.logging.RequireNotMaintenanceMode503",
        },
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
    },
    "handlers": {
        "null": {
            "class": "logging.NullHandler",
        },
        "console": {
            "level": DEBUG_LEVEL,
            "class": "logging.StreamHandler",
            "stream": sys.stdout,
        },
        "mail_admins_specific_exceptions": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
        },
    },
    "formatters": {
        "file": {
            "format": "%(asctime)s\t%(name)s\t%(levelname)s\t%(message)s",
        },
    },
    "loggers": {
        "": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": True,
        },
        "django.security.DisallowedHost": {
            "handlers": ["null"],
            "propagate": False,
        },
        "api.exceptions.UpdateSummariesException": {
            "handlers": ["mail_admins_specific_exceptions"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "mermaid_cache",
    }
}


# SIMPLEQ SETTINGS

# Max number of messages to fetch in one call.
SQS_BATCH_SIZE = 10
# Number of seconds to wait in seconds for new messages.
SQS_WAIT_SECONDS = 20
# Number of seconds before the message is visible again
# in SQS for other tasks to pull.
SQS_MESSAGE_VISIBILITY = int(os.environ.get("SQS_MESSAGE_VISIBILITY", "300"))
# Name of queue, if it doesn't exist it will be created.
QUEUE_NAME = os.environ.get("SQS_QUEUE_NAME", "mermaid-local")  # required
IMAGE_QUEUE_NAME = os.environ.get("IMAGE_SQS_QUEUE_NAME", "mermaid-local")  # required
USE_FIFO = os.environ.get("USE_FIFO", "True")
# Override default boto3 url for SQS
ENDPOINT_URL = None if ENVIRONMENT in ("dev", "prod") else "http://sqs:9324"


# IMAGE CLASSIFICATION SETTINGS

IMAGE_BUCKET_AWS_ACCESS_KEY_ID = AWS_ACCESS_KEY_ID
IMAGE_BUCKET_AWS_SECRET_ACCESS_KEY = AWS_SECRET_ACCESS_KEY
if ENVIRONMENT == "prod":
    IMAGE_BUCKET_AWS_ACCESS_KEY_ID = os.environ.get("IMAGE_BUCKET_AWS_ACCESS_KEY_ID")
    IMAGE_BUCKET_AWS_SECRET_ACCESS_KEY = os.environ.get("IMAGE_BUCKET_AWS_SECRET_ACCESS_KEY")
IMAGE_S3_PATH = "mermaid/"
DATA_UPLOAD_MAX_MEMORY_SIZE = 30 * 1024 * 1024  # 30 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 15 * 1024 * 1024  # 15 MB
MAX_IMAGE_PIXELS = 8000 * 8000
AWS_QUERYSTRING_AUTH = False
AUTOCONFIRM_THRESHOLD = 1.0
CLASSIFIED_THRESHOLD = 0.5
SPACER = {
    "AWS_ACCESS_KEY_ID": IMAGE_BUCKET_AWS_ACCESS_KEY_ID,
    "AWS_SECRET_ACCESS_KEY": IMAGE_BUCKET_AWS_SECRET_ACCESS_KEY,
    "AWS_REGION": AWS_REGION,
    "EXTRACTORS_CACHE_DIR": "/tmp/classifier",
}

# Reporting S3 credentials
REPORT_S3_ACCESS_KEY_ID = os.environ.get("REPORT_S3_ACCESS_KEY_ID")
REPORT_S3_SECRET_ACCESS_KEY = os.environ.get("REPORT_S3_SECRET_ACCESS_KEY")
