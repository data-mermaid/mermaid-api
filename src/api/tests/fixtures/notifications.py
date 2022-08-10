import pytest

from api.models import Notification


@pytest.fixture
def notification_info(profile1):
    return Notification.objects.create(
        title="Info message title",
        status=Notification.INFO,
        description='This is some info. <a href="https://google.com">link</a>',
        owner=profile1,
    )


@pytest.fixture
def notification_warning(profile1):
    return Notification.objects.create(
        title="Warning message title",
        status=Notification.WARNING,
        description="This is a warning",
        owner=profile1,
    )


@pytest.fixture
def notification_error(profile2):
    return Notification.objects.create(
        title="Error message title",
        status=Notification.ERROR,
        description="This is a error",
        owner=profile2,
    )


@pytest.fixture
def notifications(
    notification_info,
    notification_warning,
    notification_error,
):
    ...
