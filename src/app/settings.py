"""
Django settings for api project.

Generated by 'django-admin startproject' using Django 1.10.3.

For more information on this file, see
https://docs.djangoproject.com/en/1.10/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.10/ref/settings/
"""

import boto3
import os
import sys

# Options: None, DEV, PROD
ENVIRONMENT = os.environ.get('ENV') or "local"
if ENVIRONMENT:
    ENVIRONMENT = ENVIRONMENT.lower()
PROJECT_NAME = 'MERMAID API'

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    with open(os.path.join(BASE_DIR, "VERSION.txt")) as f:
        API_VERSION = f.read().replace("\n", "")
except:
    API_VERSION = "NA"

LOGIN_REDIRECT_URL = 'api-root'

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = ENVIRONMENT not in ("dev", "prod",)

if ENVIRONMENT in ('dev', 'prod'):
    ALLOWED_HOSTS = [host.strip() for host in os.environ['ALLOWED_HOSTS'].split(',')]
else:
    ALLOWED_HOSTS = ['*']

# Set to True to prevent db writes and return 503
MAINTENANCE_MODE = os.environ.get('MAINTENANCE_MODE') == 'True' or False
MAINTENANCE_MODE_IGNORE_ADMIN_SITE = os.environ.get('MAINTENANCE_MODE_IGNORE_ADMIN_SITE', True)
MAINTENANCE_MODE_IGNORE_STAFF = os.environ.get('MAINTENANCE_MODE_IGNORE_STAFF', True)
MAINTENANCE_MODE_IGNORE_SUPERUSER = os.environ.get('MAINTENANCE_MODE_IGNORE_SUPERUSER', True)
# the absolute url where users will be redirected to during maintenance-mode
# MAINTENANCE_MODE_REDIRECT_URL = 'https://datamermaid.org/'
# Other maintenance_mode settings: https://github.com/fabiocaccamo/django-maintenance-mode

ADMINS = [('Datamermaid admin', admin.strip()) for admin in os.environ['ADMINS'].split(',')]
SUPERUSER = ('Datamermaid superuser', os.environ['SUPERUSER'])
DEFAULT_DOMAIN_API = os.environ['DEFAULT_DOMAIN_API']
DEFAULT_DOMAIN_COLLECT = os.environ['DEFAULT_DOMAIN_COLLECT']

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    'maintenance_mode',
    'rest_framework',
    'rest_framework_gis',
    'django_filters',
    'django_extensions',
    'api.apps.ApiConfig',
    'tools',
    'taggit',
    'simpleq',
    'sqltables',
]
if ENVIRONMENT in ("local", ):
    INSTALLED_APPS.append("debug_toolbar")


def show_toolbar(request):
    return True


DEBUG_TOOLBAR_CONFIG = {
}
if ENVIRONMENT in ("local",):
    DEBUG_TOOLBAR_CONFIG["SHOW_TOOLBAR_CALLBACK"] = show_toolbar

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'maintenance_mode.middleware.MaintenanceModeMiddleware',
    "api.middleware.APIVersionMiddleware",
]
if ENVIRONMENT in ("local", ):
    MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware'] + MIDDLEWARE

if ENVIRONMENT in ('dev', 'prod'):
    CONN_MAX_AGE = None

ROOT_URLCONF = 'app.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR, os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'app.wsgi.application'

# from rest_framework import permissions
# class DefaultPermission(permissions.BasePermission):
#     def has_permission(self, request, view):
#         return False

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'api.auth_backends.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ),
    # 'DEFAULT_PERMISSION_CLASSES': (
    #     'api.resources.DefaultPermission',
    # ),
    'DEFAULT_FILTER_BACKENDS': ('django_filters.rest_framework.DjangoFilterBackend',),
    'DEFAULT_RENDERER_CLASSES': (
        # 'api.renderers.BaseBrowsableAPIRenderer',
        'rest_framework.renderers.JSONRenderer',
    ),
    'COERCE_DECIMAL_TO_STRING': False,
    'DEFAULT_SCHEMA_CLASS': 'rest_framework.schemas.coreapi.AutoSchema'
}

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': os.environ.get('DB_NAME') or 'mermaid',
        'USER': os.environ.get('DB_USER') or 'postgres',
        'PASSWORD': os.environ.get('DB_PASSWORD') or 'postgres',
        'HOST': os.environ.get('DB_HOST') or 'localhost',
        'PORT': os.environ.get('DB_PORT') or '5432',
    }
}

# Password validation
# https://docs.djangoproject.com/en/1.10/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/1.10/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.10/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

AWS_BACKUP_BUCKET = os.environ.get('AWS_BACKUP_BUCKET')
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.environ.get('AWS_REGION')
S3_DBBACKUP_MAXAGE = 60  # days

API_NULLQUERY = 'null'

EMAIL_HOST = os.environ.get('EMAIL_HOST')
EMAIL_PORT = os.environ.get('EMAIL_PORT')
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = 'MERMAID System <{}>'.format(EMAIL_HOST_USER)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
CORS_ORIGIN_ALLOW_ALL = True
CORS_EXPOSE_HEADERS = [
    "HTTP_API_VERSION"
]


# *****************
# **    Auth0    **
# *****************

AUTH0_DOMAIN = 'datamermaid.auth0.com'
AUTH0_USER_INFO_ENDPOINT = 'https://{domain}/userinfo'.format(domain=AUTH0_DOMAIN)

# *********
# ** API **
# *********
AUTH0_MANAGEMENT_API_AUDIENCE = os.environ.get('AUTH0_MANAGEMENT_API_AUDIENCE')
MERMAID_API_AUDIENCE = os.environ.get('MERMAID_API_AUDIENCE')
MERMAID_API_SIGNING_SECRET = os.environ.get('MERMAID_API_SIGNING_SECRET')
TAGGIT_CASE_INSENSITIVE = True
GEO_PRECISION = 6  # to nearest 10 cm

# ************
# ** CLIENT **
# ************

# MERMAID Collect (SPA)
SPA_ADMIN_CLIENT_ID = os.environ.get('SPA_ADMIN_CLIENT_ID')
SPA_ADMIN_CLIENT_SECRET = os.environ.get('SPA_ADMIN_CLIENT_SECRET')

# MERMAID Management API (Non Interactive)
MERMAID_MANAGEMENT_API_CLIENT_ID = os.environ.get('MERMAID_MANAGEMENT_API_CLIENT_ID')
MERMAID_MANAGEMENT_API_CLIENT_SECRET = os.environ.get('MERMAID_MANAGEMENT_API_CLIENT_SECRET')

# Circle CI API
CIRCLE_CI_CLIENT_ID = os.environ.get('CIRCLE_CI_CLIENT_ID')

boto3_session = boto3.session.Session(
    aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
    region_name=os.environ.get('AWS_REGION'))

# ***************
# ** MAILCHIMP **
# ***************

MC_API_KEY = os.environ.get('MC_API_KEY')
MC_USER = os.environ.get('MC_USER')
MC_LIST_ID = os.environ.get('MC_LIST_ID')


DEBUG_LEVEL = 'ERROR'
if ENVIRONMENT in ('local', 'dev'):
    DEBUG_LEVEL = 'DEBUG'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
        'console': {
            'level': DEBUG_LEVEL,
            'class': 'logging.StreamHandler',
            'stream': sys.stdout
        }
    },
    'formatters': {
        'file': {
            'format': '%(asctime)s\t%(name)s\t%(levelname)s\t%(message)s',
        },
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': True,
        },
        'django.security.DisallowedHost': {
            'handlers': ['null'],
            'propagate': False,
        },
        # 'django.db.backends': {
        #     'handlers': ['console'],
        #     'level': 'DEBUG',
        # },
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'mermaid_cache',
    }
}

if ENVIRONMENT in ("dev", "prod"):
    LOGGING["handlers"]["watchtower"] = {
        'level': DEBUG_LEVEL,
        'class': 'watchtower.CloudWatchLogHandler',
        'formatter': 'file',
        'log_group': '{}-mermaid-api'.format(ENVIRONMENT),
        'use_queues': True,
        'boto3_session': boto3_session
    }
    LOGGING["loggers"][""]["handlers"].append("watchtower")


## SIMPLEQ SETTINGS

# Max number of messages to fetch in one call.
SQS_BATCH_SIZE = 10

# Number of seconds to wait in seconds for new messages.
SQS_WAIT_SECONDS = 20

# Number of seconds before the message is visible again
# in SQS for other tasks to pull.
SQS_MESSAGE_VISIBILITY = 300

# Name of queue, if it doesn't exist it will be created.
QUEUE_NAME = f"mermaid-{ENVIRONMENT}"  # required

# Override default boto3 url for SQS
ENDPOINT_URL = None if ENVIRONMENT in ("dev", "prod") else "http://sqs:9324"

## -SIMPLEQ SETTINGS-
