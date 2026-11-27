"""Card 2293: three Django-admin permission/integrity gaps (security audit under 2231).

1. bulk_notification_view ran for any staff user, ignoring the Notification add permission.
2. ManagementAdmin.delete_view reassigned sample events before super() enforced delete permission.
3. The delete replacement was accepted from any project.
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.gis.geos import Point
from django.test import Client

from api.models import (
    Management,
    Notification,
    Profile,
    ProjectProfile,
    SampleEvent,
    Site,
)


def _staff(codenames):
    user = get_user_model().objects.create_user(
        username="vt2293", password="x", is_staff=True, is_superuser=False
    )
    for codename in codenames:
        perm = Permission.objects.filter(codename=codename).first()
        if perm:
            user.user_permissions.add(perm)
    return get_user_model().objects.get(pk=user.pk)  # reload perm cache


@pytest.fixture
def client_staff_view_only(db):
    user = _staff(["view_management", "view_notification"])
    client = Client()
    client.force_login(user)
    return client


def test_bulk_notification_requires_add_permission(db, client_staff_view_only, project1):
    members = [
        Profile.objects.create(
            email=f"vt2293-{i}@example.invalid", first_name="n", last_name=str(i)
        )
        for i in range(2)
    ]
    for m in members:
        ProjectProfile.objects.create(project=project1, profile=m, role=ProjectProfile.READONLY)

    before = Notification.objects.count()
    resp = client_staff_view_only.post(
        "/admin/api/notification/bulk_notification/",
        {"title": "vt2293", "status": "info", "description": "x", "project": str(project1.pk)},
    )
    assert resp.status_code == 403
    assert Notification.objects.count() == before


def _sample_event(project, management, country1, reef_type1, reef_zone1, reef_exposure1):
    site = Site.objects.create(
        project=project,
        name="vt2293-site",
        location=Point(0, 0),
        country=country1,
        reef_type=reef_type1,
        reef_zone=reef_zone1,
        exposure=reef_exposure1,
    )
    return SampleEvent.objects.create(site=site, management=management)


def test_delete_view_does_not_reassign_without_delete_permission(
    db, client_staff_view_only, project1, country1, reef_type1, reef_zone1, reef_exposure1
):
    mgmt = Management.objects.create(name="vt2293-A", project=project1)
    replacement = Management.objects.create(name="vt2293-A2", project=project1)
    se = _sample_event(project1, mgmt, country1, reef_type1, reef_zone1, reef_exposure1)

    resp = client_staff_view_only.post(
        f"/admin/api/management/{mgmt.pk}/delete/",
        {"replacement_obj": str(replacement.pk), "post": "yes"},
    )
    assert resp.status_code == 403  # delete denied
    se.refresh_from_db()
    assert se.management_id == mgmt.id  # NOT reassigned
    assert Management.objects.filter(pk=mgmt.pk).exists()


def test_delete_view_rejects_cross_project_replacement(
    db, project1, project2, country1, reef_type1, reef_zone1, reef_exposure1
):
    user = _staff(["view_management", "delete_management"])
    client = Client()
    client.force_login(user)

    mgmt = Management.objects.create(name="vt2293-A", project=project1)
    foreign = Management.objects.create(name="vt2293-B", project=project2)  # different project
    se = _sample_event(project1, mgmt, country1, reef_type1, reef_zone1, reef_exposure1)

    client.post(
        f"/admin/api/management/{mgmt.pk}/delete/",
        {"replacement_obj": str(foreign.pk), "post": "yes"},
    )
    se.refresh_from_db()
    assert se.management_id == mgmt.id  # cross-project replacement rejected, not applied
