"""C6: the admin page issues a key for somebody else's profile, so it has to
mint one correctly, show the secret exactly once, and never put the hash
anywhere a human or a CSV can reach it. Who may issue is the ordinary
`api.add_apikey` permission, not the superuser flag."""

from datetime import timedelta

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import Permission, User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory
from django.utils import timezone

from api.admin.base import APIKeyAdmin, APIKeyAdminForm, BaseAdmin
from api.models import APIKey
from api.resources.me import MeSerializer
from api.resources.profile import ProfileSerializer
from api.resources.project import ProjectCSVSerializer, ProjectSerializer
from api.resources.project_profile import ProjectProfileSerializer
from api.utils.apikeys import DEFAULT_LIFETIME_DAYS, generate_api_key, parse_api_key
from .fixtures.apikeys import api_key_audit_lines


@pytest.fixture
def key_admin():
    return APIKeyAdmin(APIKey, AdminSite())


def _request(user=None, method="post"):
    request = getattr(RequestFactory(), method)("/admin/api/apikey/")
    request.user = user or User(username="root", is_superuser=True, is_staff=True)
    request.session = {}
    request._messages = FallbackStorage(request)
    return request


def _staff(username, add_apikey=False):
    """A saved, non-superuser staff account, optionally holding `api.add_apikey`.

    Saved rather than in-memory because a permission check reads the account's
    permission rows, which an unsaved user has no id to be joined to.
    """

    user = User.objects.create_user(username=username, is_staff=True)
    if add_apikey:
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label="api", codename="add_apikey")
        )
    return user


def _messages(request):
    return [str(message) for message in request._messages._queued_messages]


def _make_key(profile, **kwargs):
    key_id, secret_hash, raw = generate_api_key()
    key = APIKey.objects.create(
        profile=profile,
        name=kwargs.pop("name", "admin bot"),
        key_id=key_id,
        secret_hash=secret_hash,
        expires_at=kwargs.pop("expires_at", timezone.now() + timedelta(days=30)),
        **kwargs,
    )
    return key, raw


# form: expiry is a choice, never a silent default


def test_blank_expiry_gets_the_default_lifetime(profile1, project1):
    form = APIKeyAdminForm(data={"profile": str(profile1.pk), "name": "bot"})

    assert form.is_valid(), form.errors
    expected = timezone.now() + timedelta(days=DEFAULT_LIFETIME_DAYS)
    assert abs((form.cleaned_data["expires_at"] - expected).total_seconds()) < 60


def test_never_expires_is_an_explicit_choice(profile1, project1):
    form = APIKeyAdminForm(
        data={
            "profile": str(profile1.pk),
            "name": "bot",
            "never_expires": "on",
        }
    )

    assert form.is_valid(), form.errors
    assert form.cleaned_data["expires_at"] is None


def test_expiry_date_and_never_expires_together_is_rejected(profile1, project1):
    form = APIKeyAdminForm(
        data={
            "profile": str(profile1.pk),
            "name": "bot",
            "expires_at": "2030-01-01 00:00",
            "never_expires": "on",
        }
    )

    assert form.is_valid() is False


def test_the_form_offers_no_scope_field(profile1):
    """A key is its profile's access, so there is nothing to narrow here. The
    fields the form sets are who it acts as, what it is called, and when it
    stops working."""

    form = APIKeyAdminForm(data={"profile": str(profile1.pk), "name": "bot"})

    assert "projects" not in form.fields
    assert form.is_valid(), form.errors


def test_never_expires_is_prechecked_for_a_key_with_no_expiry(profile1, project1):
    key, _ = _make_key(profile1, expires_at=None)

    form = APIKeyAdminForm(instance=key)

    assert form.fields["never_expires"].initial is True


# creation through the add form


def test_save_model_generates_the_key_and_shows_the_secret_once(key_admin, profile1, project1):
    request = _request()
    form = APIKeyAdminForm(data={"profile": str(profile1.pk), "name": "ingest bot"})
    assert form.is_valid(), form.errors

    key = form.save(commit=False)
    key_admin.save_model(request, key, form, change=False)

    saved = APIKey.objects.get(pk=form.instance.pk)
    assert len(saved.key_id) == 12
    assert len(saved.secret_hash) == 64

    banners = _messages(request)
    assert len(banners) == 1
    raw = banners[0].split("<code>")[1].split("</code>")[0]
    _env, key_id, secret = parse_api_key(raw)
    assert key_id == saved.key_id
    # The banner is the only place the secret exists; nothing stored it.
    assert secret not in banners[0].replace(raw, "")
    assert saved.secret_hash not in banners[0]

    # ...and only on creation: saving the row again has nothing left to show.
    key_admin.save_model(request, saved, form, change=True)
    assert len(_messages(request)) == 1


def test_creation_leaves_an_audit_line(key_admin, profile1, project1, api_key_audit_logs):
    """C8: a minted credential is logged with who asked for it and who it acts
    as, and never with the secret or the hash."""

    request = _request()
    form = APIKeyAdminForm(data={"profile": str(profile1.pk), "name": "audited bot"})
    assert form.is_valid(), form.errors

    key = form.save(commit=False)
    key_admin.save_model(request, key, form, change=False)

    saved = APIKey.objects.get(pk=form.instance.pk)
    lines = api_key_audit_lines(api_key_audit_logs, "created")
    assert len(lines) == 1
    assert f"key_id={saved.key_id}" in lines[0]
    assert f"profile={profile1.pk}" in lines[0]
    assert "actor=root" in lines[0]
    assert "replaces=none" in lines[0]
    assert saved.secret_hash not in lines[0]

    raw = _messages(request)[0].split("<code>")[1].split("</code>")[0]
    assert parse_api_key(raw)[2] not in lines[0]


def test_replacement_creation_names_the_key_it_replaces(
    key_admin, profile1, project1, api_key_audit_logs
):
    original, _ = _make_key(profile1, name="nightly job")

    key_admin.generate_replacement_keys(_request(), APIKey.objects.filter(pk=original.pk))

    replacement = APIKey.objects.exclude(pk=original.pk).get()
    lines = api_key_audit_lines(api_key_audit_logs, "created")
    assert len(lines) == 1
    assert f"key_id={replacement.key_id}" in lines[0]
    assert f"replaces={original.key_id}" in lines[0]


def test_editing_a_key_does_not_reissue_the_secret(key_admin, profile1, project1):
    key, _ = _make_key(profile1)
    original_key_id = key.key_id
    original_hash = key.secret_hash
    request = _request()

    key.name = "renamed"
    key_admin.save_model(request, key, form=None, change=True)

    key.refresh_from_db()
    assert key.key_id == original_key_id
    assert key.secret_hash == original_hash
    assert _messages(request) == []


def test_adding_a_key_takes_the_add_permission_not_the_superuser_flag(key_admin, db):
    """Issuing is not a superuser action. Staff who hold `api.add_apikey` can
    issue, and staff who do not, cannot; the flag itself decides nothing."""

    superuser = _request()
    permitted = _request(user=_staff("keyissuer", add_apikey=True))
    unpermitted = _request(user=_staff("keyreader"))

    assert key_admin.has_add_permission(superuser) is True
    assert key_admin.has_add_permission(permitted) is True
    assert key_admin.has_add_permission(unpermitted) is False


def test_profile_is_locked_once_a_key_exists(key_admin, profile1, project1):
    key, _ = _make_key(profile1)
    request = _request()

    assert "profile" not in key_admin.get_readonly_fields(request)
    assert "profile" in key_admin.get_readonly_fields(request, obj=key)


# actions


def test_revoke_action_revokes_the_selection(key_admin, profile1, project1):
    key, _ = _make_key(profile1)
    request = _request()

    key_admin.revoke_keys(request, APIKey.objects.filter(pk=key.pk))

    key.refresh_from_db()
    assert key.is_usable is False
    assert key.revoked_at is not None
    assert "root" in key.revoked_reason


def test_generate_replacement_keeps_the_profile_and_leaves_the_original(key_admin, profile1):
    key, _ = _make_key(profile1, name="nightly job")
    request = _request()

    key_admin.generate_replacement_keys(request, APIKey.objects.filter(pk=key.pk))

    replacement = APIKey.objects.exclude(pk=key.pk).get()
    assert replacement.profile == profile1
    assert replacement.name == "nightly job"
    assert replacement.key_id != key.key_id
    assert replacement.secret_hash != key.secret_hash
    assert replacement.expires_at is not None

    key.refresh_from_db()
    assert key.is_usable is True

    raw = _messages(request)[0].split("<code>")[1].split("</code>")[0]
    assert parse_api_key(raw)[1] == replacement.key_id


def test_replacing_a_no_expiry_key_stays_no_expiry(key_admin, profile1, project1):
    key, _ = _make_key(profile1, expires_at=None)

    key_admin.generate_replacement_keys(_request(), APIKey.objects.filter(pk=key.pk))

    assert APIKey.objects.exclude(pk=key.pk).get().expires_at is None


def test_the_replacement_action_follows_the_add_permission(key_admin, profile1, project1):
    """A replacement is a new key, so the action is offered to whoever may add
    one and withheld from whoever may not. Revoking stays open to all staff."""

    key, _ = _make_key(profile1)
    permitted = _request(user=_staff("keyissuer", add_apikey=True))
    unpermitted = _request(user=_staff("keyreader"))

    assert "generate_replacement_keys" in key_admin.get_actions(permitted)
    assert "generate_replacement_keys" not in key_admin.get_actions(unpermitted)
    assert "revoke_keys" in key_admin.get_actions(unpermitted)

    key_admin.generate_replacement_keys(permitted, APIKey.objects.filter(pk=key.pk))
    assert APIKey.objects.count() == 2


# the hash never reaches a human, a page, or a CSV


def test_admin_never_exposes_the_hash(key_admin, profile1, project1):
    key, _ = _make_key(profile1)
    request = _request(method="get")

    assert "secret_hash" not in key_admin.list_display
    assert "secret_hash" not in key_admin.exportable_fields
    assert "secret_hash" not in key_admin.get_fields(request, obj=key)
    assert "secret_hash" not in APIKeyAdminForm(instance=key).fields
    assert "secret_hash" not in key_admin.get_readonly_fields(request, obj=key)
    assert key.secret_hash not in str(key)


def test_admin_offers_no_all_fields_export(key_admin):
    # BaseAdmin's all-fields export walks every concrete field, secret_hash
    # included, so this page must not inherit it.
    assert isinstance(key_admin, BaseAdmin) is False
    assert "export_model_all_as_csv" not in key_admin.get_actions(_request())


def test_no_expiry_keys_are_one_click_away(key_admin, profile1, project1):
    forever, _ = _make_key(profile1, expires_at=None)
    expiring, _ = _make_key(profile1)
    expiry_filter = key_admin.list_filter[0]
    queryset = APIKey.objects.all()

    def filtered(value):
        request = _request(method="get")
        instance = expiry_filter(request, {"expiry": [value]}, APIKey, key_admin)
        return list(instance.queryset(request, queryset))

    assert filtered("never") == [forever]
    assert filtered("set") == [expiring]


# leak checks: the new reverse relation on Profile stays out of the API


def test_me_response_has_no_api_keys(api_client1, profile1, project1):
    _make_key(profile1)

    response = api_client1.get("/v1/me/", format="json")

    assert response.status_code == 200
    assert "api_keys" not in response.json()


def test_project_profiles_response_has_no_api_keys(api_client1, profile1, project1):
    _make_key(profile1)

    response = api_client1.get(f"/v1/projects/{project1.pk}/project_profiles/", format="json")

    assert response.status_code == 200
    for record in response.json()["results"]:
        assert "api_keys" not in record
        assert "secret_hash" not in record


def test_profiles_response_has_no_api_keys(api_client1, profile1, project1):
    _make_key(profile1)

    response = api_client1.get("/v1/profiles/", format="json")

    assert response.status_code == 200
    for record in response.json()["results"]:
        assert "api_keys" not in record


def test_sync_pull_project_profiles_has_no_api_keys(db_setup, api_client1, profile1, project1):
    """The sync registry serializes ProjectProfile and Project through the same
    viewsets; `api_keys` is a new reverse relation on Profile, so a pull is
    where a depth-based or `__all__` serializer would leak it."""

    _make_key(profile1)
    data = {
        "project_profiles": {"last_revision": None, "project": str(project1.pk)},
        "projects": {"last_revision": None, "project": str(project1.pk)},
    }

    response = api_client1.post("/v1/pull/", data, format="json")

    assert response.status_code == 200
    body = response.json()
    for source_type in ("project_profiles", "projects"):
        updates = body[source_type]["updates"]
        assert updates
        for record in updates:
            assert "api_keys" not in record
            assert "secret_hash" not in record
    assert "secret_hash" not in response.content.decode()
    assert "api_keys" not in response.content.decode()


def test_profile_and_project_serializers_declare_no_key_fields():
    """A guard for the next serializer someone writes over Profile or Project:
    `api_keys` is a new reverse relation and `secret_hash` must never be a
    field name anywhere the API renders."""

    for serializer_class in (
        MeSerializer,
        ProfileSerializer,
        ProjectSerializer,
        ProjectCSVSerializer,
        ProjectProfileSerializer,
    ):
        fields = set(serializer_class().fields)
        assert "api_keys" not in fields, serializer_class.__name__
        assert "secret_hash" not in fields, serializer_class.__name__
