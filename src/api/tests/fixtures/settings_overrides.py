import pytest


@pytest.fixture()
def disable_recaptcha(settings):
    settings.DRF_RECAPTCHA_TESTING = True
