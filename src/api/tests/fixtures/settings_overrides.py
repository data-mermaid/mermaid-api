import pytest

# Shared across image-bucket-routing and inference-lane tests: a prod-like
# environment with distinct prod/test buckets and credentials, so the per-bucket
# branches are all reachable.
STORAGE_SETTINGS = {
    "IMAGE_PROCESSING_BUCKET": "prod-bucket",
    "IMAGE_PROCESSING_BUCKET_TEST": "test-bucket",
    "IMAGE_BUCKET_AWS_ACCESS_KEY_ID": "image-key",
    "IMAGE_BUCKET_AWS_SECRET_ACCESS_KEY": "image-secret",
    "AWS_ACCESS_KEY_ID": "default-key",
    "AWS_SECRET_ACCESS_KEY": "default-secret",
    "IMAGE_S3_PATH": "mermaid/",
    "IMAGE_S3_PATH_TEST": "mermaid-production-test/",
}


@pytest.fixture()
def disable_recaptcha(settings):
    settings.DRF_RECAPTCHA_TESTING = True


@pytest.fixture()
def email_backend(settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
