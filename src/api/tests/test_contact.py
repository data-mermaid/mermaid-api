from django.conf import settings
from django.core import mail
from django.urls import reverse
from rest_framework import status

MESSAGE_POST = {
    "name": "Test User",
    "email": "test@datamermaid.org",
    "subject": "test subject",
    "message": "test message",
    "recaptcha": "foo",
}


def test_contact_mermaid(
    client,
    db_setup,
    email_backend,
    disable_recaptcha,
):
    # uncomment once pytest/simpleq environment is sorted out
    pass
    # url = reverse("contactmermaid")
    # response = client.post(url, data=MESSAGE_POST, content_type="application/json")
    # assert response.status_code == status.HTTP_200_OK
    # assert len(mail.outbox) == 1
    # sent_email = mail.outbox[0]
    # assert sent_email.to == [settings.SUPERUSER[1]]
    # assert sent_email.reply_to == [MESSAGE_POST["email"]]
    # mail.outbox = []


def test_contact_project_admins(
    client,
    db_setup,
    email_backend,
    project1,
    profile1,
    belt_fish_project,
    disable_recaptcha,
):
    pass
    # message_post = dict(MESSAGE_POST, project=project1.pk)
    # url = reverse("contactprojectadmins")
    # response = client.post(url, data=message_post, content_type="application/json")
    # assert response.status_code == status.HTTP_200_OK
    # assert len(mail.outbox) == 1
    # sent_email = mail.outbox[0]
    # assert sent_email.to == [profile1.email]
    # assert sent_email.reply_to == [message_post["email"]]
    # mail.outbox = []


def test_contact_project_admins_badrecaptcha(
    client,
    db_setup,
    email_backend,
    project1,
    profile1,
    belt_fish_project,
):
    pass
    # message_post = dict(MESSAGE_POST, project=project1.pk)
    # url = reverse("contactprojectadmins")
    # response = client.post(url, data=message_post, content_type="application/json")
    # assert response.status_code == status.HTTP_400_BAD_REQUEST
    # assert len(mail.outbox) == 0
