"""C4: a key stops working when it should.

A key acts as its profile, so losing a project membership takes the key's
access to that project with it on the next request - that is covered in
test_api_key_permissions. What is left here is the key's own end of life:
explicit revocation, expiry, and the daily task that keeps the admin list
honest about which keys are still live."""

from datetime import timedelta
from io import StringIO

import pytest
from django.core.cache import cache
from django.core.management import call_command
from django.utils import timezone
from rest_framework import exceptions
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from api.auth_backends import APIKeyAuthentication
from api.models import APIKey
from api.signals.apikeys import PROFILE_DEACTIVATED
from api.utils.apikeys import generate_api_key
from .fixtures.apikeys import api_key_audit_lines


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


def _make_key(profile, name="lifecycle bot", **kwargs):
    key_id, secret_hash, raw = generate_api_key()
    key = APIKey.objects.create(
        profile=profile,
        name=name,
        key_id=key_id,
        secret_hash=secret_hash,
        expires_at=kwargs.pop("expires_at", timezone.now() + timedelta(days=365)),
        **kwargs,
    )
    return key, raw


# revoke()


def test_revoke_sets_all_three_fields(profile1, project1):
    key, _ = _make_key(profile1)

    assert key.revoke("manual") is True

    key.refresh_from_db()
    assert key.revoked_at is not None
    assert key.revoked_reason == "manual"
    assert key.is_active is False
    assert key.is_usable is False


def test_revoke_is_idempotent(profile1, project1):
    key, _ = _make_key(profile1)
    key.revoke("first")
    first_revoked_at = key.revoked_at

    # A second revoke must not rewrite when the key stopped working.
    assert key.revoke("second") is False
    key.refresh_from_db()
    assert key.revoked_at == first_revoked_at
    assert key.revoked_reason == "first"


def test_revoke_logs_the_audit_line(profile1, project1, api_key_audit_logs):
    """C8: creation and revocation both leave a line naming the key, the
    profile, who did it and why."""

    key, _ = _make_key(profile1)
    key.revoke("manual", actor="someone@example.com")

    logged = api_key_audit_lines(api_key_audit_logs, "revoked")
    assert len(logged) == 1
    assert f"key_id={key.key_id}" in logged[0]
    assert f"profile={profile1.pk}" in logged[0]
    assert "actor=someone@example.com" in logged[0]
    assert "reason=manual" in logged[0]


def test_revoke_from_a_signal_names_the_system_as_actor(profile1, project1, api_key_audit_logs):
    key, _ = _make_key(profile1)
    key.revoke(PROFILE_DEACTIVATED)

    logged = api_key_audit_lines(api_key_audit_logs, "revoked")
    assert "actor=system" in logged[0]


def test_is_expired_and_is_usable(profile1, project1):
    live, _ = _make_key(profile1)
    assert live.is_expired is False
    assert live.is_usable is True

    expired, _ = _make_key(
        profile1, name="expired", expires_at=timezone.now() - timedelta(seconds=1)
    )
    assert expired.is_expired is True
    assert expired.is_usable is False

    never, _ = _make_key(profile1, name="never", expires_at=None)
    assert never.is_expired is False
    assert never.is_usable is True


def test_revoked_key_no_longer_authenticates(profile1, project1, project_profile1):
    key, raw = _make_key(profile1)
    request = Request(APIRequestFactory().get("/v1/projects/", HTTP_AUTHORIZATION=f"ApiKey {raw}"))

    assert APIKeyAuthentication().authenticate(request) is not None

    key.revoke("manual")

    with pytest.raises(exceptions.AuthenticationFailed):
        APIKeyAuthentication().authenticate(request)


def test_deactivating_a_profile_revokes_its_keys(profile1, profile2, project1):
    """Profile has no is_active flag today, so this drives the signal directly:
    if one is ever added, the keys stop at the same moment the account does."""

    key, _ = _make_key(profile1)
    other, _ = _make_key(profile2, name="other profile bot")

    profile1.is_active = False
    profile1.save()

    key.refresh_from_db()
    other.refresh_from_db()
    assert key.is_active is False
    assert key.revoked_reason == PROFILE_DEACTIVATED
    assert other.revoked_at is None


# daily task


def _run_maintenance(**kwargs):
    out = StringIO()
    call_command("api_key_maintenance", stdout=out, **kwargs)
    return out.getvalue()


def test_daily_task_deactivates_expired_keys(profile1, project1):
    expired, _ = _make_key(profile1, name="expired", expires_at=timezone.now() - timedelta(days=1))
    live, _ = _make_key(profile1, name="live")

    output = _run_maintenance()

    expired.refresh_from_db()
    live.refresh_from_db()
    assert expired.is_active is False
    # Expiry is not revocation; revoked_at stays null so the two are
    # distinguishable in the audit trail.
    assert expired.revoked_at is None
    assert live.is_active is True
    assert "deactivated 1 expired key(s)" in output


def test_daily_task_leaves_no_expiry_keys_active(profile1, project1):
    never, _ = _make_key(profile1, name="never", expires_at=None)

    _run_maintenance()

    never.refresh_from_db()
    assert never.is_active is True


def test_daily_task_dry_run_writes_nothing(profile1, project1):
    expired, _ = _make_key(profile1, name="expired", expires_at=timezone.now() - timedelta(days=1))

    output = _run_maintenance(dry_run=True)

    expired.refresh_from_db()
    assert expired.is_active is True
    assert "would deactivate 1 expired key(s)" in output


def test_daily_task_reports_stale_no_expiry_keys(profile1, project1, api_key_audit_logs):
    stale, _ = _make_key(profile1, name="stale", expires_at=None)
    APIKey.objects.filter(pk=stale.pk).update(last_used_at=timezone.now() - timedelta(days=200))

    recent, _ = _make_key(profile1, name="recent", expires_at=None)
    APIKey.objects.filter(pk=recent.pk).update(last_used_at=timezone.now() - timedelta(days=10))

    output = _run_maintenance()

    assert "1 no-expiry key(s) unused for 180 days" in output
    stale_logs = api_key_audit_lines(api_key_audit_logs, "stale")
    assert len(stale_logs) == 1
    assert stale.key_id in stale_logs[0]
    assert recent.key_id not in stale_logs[0]


def test_daily_task_reports_never_used_old_key_as_stale(profile1, project1):
    never_used, _ = _make_key(profile1, name="never used", expires_at=None)
    APIKey.objects.filter(pk=never_used.pk).update(created_on=timezone.now() - timedelta(days=200))

    output = _run_maintenance()

    assert "1 no-expiry key(s) unused for 180 days" in output


def test_daily_task_stale_report_ignores_keys_with_an_expiry(profile1, project1):
    # A key with an expiry date has an end already; only the never-expiring
    # ones are the forgotten-credential risk the report is for.
    with_expiry, _ = _make_key(profile1, name="with expiry")
    APIKey.objects.filter(pk=with_expiry.pk).update(
        last_used_at=timezone.now() - timedelta(days=200)
    )

    output = _run_maintenance()

    assert "0 no-expiry key(s) unused for 180 days" in output
