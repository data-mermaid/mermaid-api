import pytest


@pytest.fixture()
def disable_recaptcha(settings):
    settings.DRF_RECAPTCHA_TESTING = True


@pytest.fixture()
def email_backend(settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
