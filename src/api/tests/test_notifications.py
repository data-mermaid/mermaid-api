from django.urls import reverse

from api.models import Notification
from api.utils.notification import add_notification


def test_restricted_notification_methods(db_setup, api_client1, notification_info):
    url = reverse("notification-list")

    request = api_client1.post(url, format="json")
    assert request.status_code == 405

    url_kwargs = {"pk": notification_info.pk}
    url = reverse("notification-detail", kwargs=url_kwargs)
    request = api_client1.put(url, {}, format="json")
    assert request.status_code == 405


def test_retrieving_notifications(
    db_setup, api_client1, profile1, notifications, notification_info
):
    url = reverse("notification-list")
    request = api_client1.get(url)
    assert request.status_code == 200
    response_data = request.json()

    assert response_data["count"] == Notification.objects.filter(owner=profile1).count()


def test_deleting_notification(db_setup, api_client1, profile1, notifications, notification_info):
    num_notifications = Notification.objects.filter(owner=profile1).count()
    url_kwargs = {"pk": notification_info.pk}
    url = reverse("notification-detail", kwargs=url_kwargs)
    request = api_client1.delete(url)
    assert request.status_code == 204

    assert Notification.objects.filter(owner=profile1).count() == num_notifications - 1


def test_delete_others_notification(db_setup, api_client2, notifications, notification_info):
    url_kwargs = {"pk": notification_info.pk}
    url = reverse("notification-detail", kwargs=url_kwargs)
    request = api_client2.delete(url)
    assert request.status_code == 404


def test_notification_title_truncation(db_setup, profile1):
    """Test that notification titles longer than the field max_length are truncated."""
    max_title_length = Notification._meta.get_field("title").max_length

    # Create a title that exceeds the max length
    long_title = "A" * (max_title_length + 50)
    template = "notifications/admins_admins_change.txt"
    context = {}

    # Clear existing notifications for profile1
    Notification.objects.filter(owner=profile1).delete()

    # Add notification with long title
    add_notification(long_title, Notification.INFO, template, context, [profile1])

    # Verify notification was created with truncated title
    notification = Notification.objects.filter(owner=profile1).first()
    assert notification is not None
    assert len(notification.title) == max_title_length
    assert notification.title.endswith("...")
    assert notification.title == long_title[: max_title_length - 3] + "..."


def test_notification_title_not_truncated_when_short(db_setup, profile1):
    """Test that notification titles shorter than the field max_length are not modified."""
    max_title_length = Notification._meta.get_field("title").max_length

    short_title = "Short notification title"
    template = "notifications/admins_admins_change.txt"
    context = {}

    # Clear existing notifications for profile1
    Notification.objects.filter(owner=profile1).delete()

    # Add notification with short title
    add_notification(short_title, Notification.INFO, template, context, [profile1])

    # Verify notification was created with original title
    notification = Notification.objects.filter(owner=profile1).first()
    assert notification is not None
    assert notification.title == short_title
    assert len(notification.title) < max_title_length
