from io import StringIO

from django.core.management import call_command

from api.models import Notification, Profile, ProjectProfile

WJ = "⁠"


def _make_bad(email):
    # bypass Profile.save() normalization to simulate pre-fix data
    profile = Profile.objects.create(email="placeholder@test.com")
    Profile.objects.filter(pk=profile.pk).update(email=email)
    profile.refresh_from_db()
    return profile


def test_fix_profile_emails_merges_into_clean_twin(db_setup, project1, profile1):
    real = Profile.objects.create(email="real@test.com")
    bad1 = _make_bad(f"{WJ}real@test.com")
    bad2 = _make_bad(f"{WJ}{WJ}real@test.com")
    ProjectProfile.objects.create(project=project1, profile=bad1, role=ProjectProfile.COLLECTOR)
    ProjectProfile.objects.create(project=project1, profile=bad2, role=ProjectProfile.COLLECTOR)
    Notification.objects.create(title="x", status=Notification.INFO, owner=bad1)

    out = StringIO()
    call_command("fix_profile_emails", "--dry-run", stdout=out)
    assert Profile.objects.filter(pk__in=[bad1.pk, bad2.pk]).count() == 2
    assert "already a member" in out.getvalue()  # dry run sees cumulative effect

    call_command("fix_profile_emails", stdout=StringIO())
    assert not Profile.objects.filter(pk__in=[bad1.pk, bad2.pk]).exists()
    pp = ProjectProfile.objects.get(project=project1, profile=real)
    assert pp.role == ProjectProfile.COLLECTOR
    assert not Notification.objects.filter(owner_id__in=[bad1.pk, bad2.pk]).exists()
    # membership move is silent: no "user added" notification for the real user
    assert not Notification.objects.filter(owner=real).exists()


def test_fix_profile_emails_cleans_in_place_without_twin(db_setup):
    bad = _make_bad(f"{WJ}solo@test.com")
    call_command("fix_profile_emails", stdout=StringIO())
    bad.refresh_from_db()
    assert bad.email == "solo@test.com"


def test_fix_profile_emails_preserves_admin_role_on_move(db_setup, project1):
    real = Profile.objects.create(email="admin-real@test.com")
    bad = _make_bad(f"{WJ}admin-real@test.com")
    ProjectProfile.objects.create(project=project1, profile=bad, role=ProjectProfile.ADMIN)

    call_command("fix_profile_emails", stdout=StringIO())
    assert ProjectProfile.objects.get(project=project1, profile=real).role == ProjectProfile.ADMIN


def test_fix_profile_emails_skips_on_role_conflict(db_setup, project1):
    real = Profile.objects.create(email="conflict@test.com")
    bad = _make_bad(f"{WJ}conflict@test.com")
    ProjectProfile.objects.create(project=project1, profile=real, role=ProjectProfile.READONLY)
    bad_pp = ProjectProfile.objects.create(project=project1, profile=bad, role=ProjectProfile.ADMIN)

    out = StringIO()
    call_command("fix_profile_emails", stdout=out)
    assert "SKIPPED, role conflict" in out.getvalue()
    assert ProjectProfile.objects.get(project=project1, profile=real).role == (
        ProjectProfile.READONLY
    )
    assert ProjectProfile.objects.filter(pk=bad_pp.pk, role=ProjectProfile.ADMIN).exists()
    assert Profile.objects.filter(pk=bad.pk).exists()
