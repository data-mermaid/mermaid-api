from contextlib import contextmanager
from unittest.mock import patch

import pytest
from django.urls import reverse

from api.models import Notification, Profile, ProjectProfile
from api.utils.email import email_project_admins
from api.utils.project import email_members_of_new_project

PLACEHOLDER_EMAIL = "placeholder@bogus.test"
NEW_USER_TEMPLATE = "emails/new_user_added_to_project.html"
ADD_REMOVE_TEMPLATE = "emails/user_project_add_remove.html"
ADMINS_CHANGE_TEMPLATE = "emails/admins_admins_change.html"


@contextmanager
def capture_emails():
    """Collect (template, to) for every mermaid_email call made by the notification paths."""
    sent = []

    def _record(*args, **kwargs):
        template = kwargs.get("template", args[1] if len(args) > 1 else None)
        to = kwargs.get("to", args[2] if len(args) > 2 else None)
        sent.append((template, list(to)))

    with (
        patch("api.notifications.mermaid_email", side_effect=_record),
        patch("api.utils.email.mermaid_email", side_effect=_record),
        patch("api.utils.project.mermaid_email", side_effect=_record),
    ):
        yield sent


def _recipients(sent, template=None):
    return [email for t, to in sent if template is None or t == template for email in to]


@pytest.fixture
def accountless_profile():
    return Profile.objects.create(email=PLACEHOLDER_EMAIL)


@pytest.fixture
def accountless_admin(project1, accountless_profile):
    return ProjectProfile.objects.create(
        project=project1, profile=accountless_profile, role=ProjectProfile.ADMIN
    )


def _add_profile(api_client, project, email, role):
    url = reverse("project-add-profile", kwargs=dict(pk=project.pk))
    return api_client.post(url, data={"email": email, "role": role}, format="json")


def test_add_accountless_profile_emails_new_profile_once(
    api_client1, project1, project_profile1, project_profile2
):
    with capture_emails() as sent:
        response = _add_profile(api_client1, project1, PLACEHOLDER_EMAIL, ProjectProfile.COLLECTOR)
    assert response.status_code == 200

    assert _recipients(sent).count(PLACEHOLDER_EMAIL) == 1
    assert _recipients(sent, NEW_USER_TEMPLATE) == [PLACEHOLDER_EMAIL]
    # Existing members get the generic notice, not the sign-up invitation
    assert sorted(_recipients(sent, ADD_REMOVE_TEMPLATE)) == sorted(
        [project_profile1.profile.email, project_profile2.profile.email]
    )


def test_add_accountless_admin_emails_new_profile_once(
    api_client1, project1, project_profile1, project_profile2
):
    with capture_emails() as sent:
        response = _add_profile(api_client1, project1, PLACEHOLDER_EMAIL, ProjectProfile.ADMIN)
    assert response.status_code == 200

    assert _recipients(sent).count(PLACEHOLDER_EMAIL) == 1
    assert _recipients(sent, ADMINS_CHANGE_TEMPLATE) == [project_profile1.profile.email]


def test_add_profile_skips_accountless_members(
    api_client1, project1, project_profile1, accountless_admin, profile3
):
    with capture_emails() as sent:
        response = _add_profile(api_client1, project1, profile3.email, ProjectProfile.COLLECTOR)
    assert response.status_code == 200

    assert PLACEHOLDER_EMAIL not in _recipients(sent)
    assert _recipients(sent, ADD_REMOVE_TEMPLATE).count(profile3.email) == 1
    assert project_profile1.profile.email in _recipients(sent, ADD_REMOVE_TEMPLATE)
    # In-app notifications still go to accountless members
    assert Notification.objects.filter(owner=accountless_admin.profile).exists()


def test_successive_accountless_adds_do_not_email_earlier_placeholders(
    api_client1, project1, project_profile1
):
    emails = [f"placeholder{i}@bogus.test" for i in range(5)]
    with capture_emails() as sent:
        for email in emails:
            _add_profile(api_client1, project1, email, ProjectProfile.ADMIN)

    recipients = _recipients(sent)
    for email in emails:
        assert recipients.count(email) == 1


def test_admin_save_without_role_change_sends_nothing(project_profile1, project_profile2):
    pp = ProjectProfile.objects.get(pk=project_profile1.pk)
    with capture_emails() as sent:
        pp.save()
    assert sent == []


def test_promotion_and_demotion_notify_admins_once(project_profile1, project_profile2):
    pp = ProjectProfile.objects.get(pk=project_profile2.pk)
    pp.role = ProjectProfile.ADMIN
    with capture_emails() as sent:
        pp.save()
    assert len(sent) == 1
    assert sorted(_recipients(sent, ADMINS_CHANGE_TEMPLATE)) == sorted(
        [project_profile1.profile.email, project_profile2.profile.email]
    )

    pp = ProjectProfile.objects.get(pk=project_profile2.pk)
    pp.role = ProjectProfile.COLLECTOR
    with capture_emails() as sent:
        pp.save()
    assert len(sent) == 1
    assert ADMINS_CHANGE_TEMPLATE == sent[0][0]


def test_resaving_promoted_instance_does_not_renotify(project_profile1, project_profile2):
    pp = ProjectProfile.objects.get(pk=project_profile2.pk)
    pp.role = ProjectProfile.ADMIN
    pp.save()
    with capture_emails() as sent:
        pp.save()
    assert sent == []


def test_project_change_skips_accountless_admins(project1, project_profile1, accountless_admin):
    project = type(project1).objects.get(pk=project1.pk)
    project.name = "Renamed project"
    with capture_emails() as sent:
        project.save()
    assert _recipients(sent) == [project_profile1.profile.email]


def test_remove_accountless_profile_sends_no_email_to_it(
    api_client1, project1, project_profile1, accountless_admin
):
    url = reverse(
        "project_profile-detail", kwargs={"project_pk": project1.pk, "pk": accountless_admin.pk}
    )
    with capture_emails() as sent:
        response = api_client1.delete(url)
    assert response.status_code == 204
    assert PLACEHOLDER_EMAIL not in _recipients(sent)
    assert project_profile1.profile.email in _recipients(sent)


def test_contact_project_admins_skips_accountless(project1, project_profile1, accountless_admin):
    with capture_emails() as sent:
        email_project_admins(
            from_email="someone@example.com",
            project=project1.pk,
            message="hi",
            name="Someone",
            subject="Question",
        )
    assert _recipients(sent) == [project_profile1.profile.email]


def test_email_members_of_new_project_skips_accountless(
    project1, project_profile1, project_profile2, accountless_admin
):
    with capture_emails() as sent:
        email_members_of_new_project(project1, project_profile1.profile)
    assert _recipients(sent) == [project_profile2.profile.email]
