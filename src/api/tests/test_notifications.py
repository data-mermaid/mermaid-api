from django.urls import reverse

from api.models import Notification


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


def test_deleting_notification(
    db_setup, api_client1, profile1, notifications, notification_info
):
    num_notifications = Notification.objects.filter(owner=profile1).count()
    url_kwargs = {"pk": notification_info.pk}
    url = reverse("notification-detail", kwargs=url_kwargs)
    request = api_client1.delete(url)
    assert request.status_code == 204

    assert Notification.objects.filter(owner=profile1).count() == num_notifications - 1


def test_delete_others_notification(
    db_setup, api_client2, notifications, notification_info
):
    url_kwargs = {"pk": notification_info.pk}
    url = reverse("notification-detail", kwargs=url_kwargs)
    request = api_client2.delete(url)
    assert request.status_code == 404
