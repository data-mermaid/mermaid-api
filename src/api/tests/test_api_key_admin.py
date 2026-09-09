"""C6: the admin page issues a key for somebody else's profile, so it has to
mint one correctly, show the secret exactly once, and never put the hash
anywhere a human or a CSV can reach it. Who may issue is the ordinary
`api.add_apikey` permission, not the superuser flag."""

from datetime import timedelta

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import Permission, User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.template.response import TemplateResponse
from django.test import RequestFactory
from django.utils import timezone

from api.admin.base import (
    APIKeyAdmin,
    APIKeyAdminForm,
    BaseAdmin,
    ProfileAdmin,
    export_model_display_as_csv,
)
from api.models import APIKey, Profile
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


def _issued(response):
    """The (key, raw) pairs the response body carries.

    The secret is only ever in a response body, so this is where a test reads
    it from; `_messages` is what asserts it is *not* in the cookie-backed
    message queue.
    """

    return [(item["key"], item["raw"]) for item in response.context_data["issued"]]


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
    response = key_admin.response_add(request, key)

    saved = APIKey.objects.get(pk=form.instance.pk)
    assert len(saved.key_id) == 12
    assert len(saved.secret_hash) == 64

    issued = _issued(response)
    assert len(issued) == 1
    shown_key, raw = issued[0]
    assert shown_key.pk == saved.pk
    _env, key_id, secret = parse_api_key(raw)
    assert key_id == saved.key_id
    assert saved.secret_hash not in raw

    # ...and only on creation: saving the row again has nothing left to show,
    # so the add response falls back to the ordinary redirect.
    delattr(request, "_issued_api_key")
    key_admin.save_model(request, saved, form, change=True)
    assert hasattr(request, "_issued_api_key") is False


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

    raw = _issued(key_admin.response_add(request, saved))[0][1]
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


def test_the_secret_never_reaches_the_message_store(key_admin, profile1, project1):
    """The raw key goes in the response body and nowhere else.

    The messages framework is not a delivery channel for it: MESSAGE_STORAGE
    defaults to FallbackStorage, which writes the message into a client-side
    cookie that is Secure only when SESSION_COOKIE_SECURE is on, and falls back
    to the session past 4096 bytes. Either way the secret would be persisted by
    the browser and replayed on the next admin request.
    """

    request = _request()
    form = APIKeyAdminForm(data={"profile": str(profile1.pk), "name": "ingest bot"})
    assert form.is_valid(), form.errors

    key_admin.save_model(request, form.save(commit=False), form, change=False)
    raw = _issued(key_admin.response_add(request, form.instance))[0][1]

    assert _messages(request) == []
    assert raw not in str(request.session)


def test_the_replacement_action_keeps_the_secrets_out_of_the_message_store(
    key_admin, profile1, project1
):
    """One page for the selection, not one banner per row: a banner per row is
    a secret per cookie, and enough rows silently spill to the session."""

    first, _ = _make_key(profile1, name="nightly job")
    second, _ = _make_key(profile1, name="hourly job")
    request = _request()

    response = key_admin.generate_replacement_keys(
        request, APIKey.objects.filter(pk__in=[first.pk, second.pk])
    )

    issued = _issued(response)
    assert len(issued) == 2
    assert _messages(request) == []
    for _key, raw in issued:
        assert raw not in str(request.session)


def test_the_add_response_renders_the_key_instead_of_redirecting(key_admin, profile1, project1):
    """A redirect is what would force the secret into cookie-backed storage to
    survive it, so the add view ends on a page that carries the key itself."""

    request = _request()
    form = APIKeyAdminForm(data={"profile": str(profile1.pk), "name": "ingest bot"})
    assert form.is_valid(), form.errors

    key_admin.save_model(request, form.save(commit=False), form, change=False)
    response = key_admin.response_add(request, form.instance)

    assert isinstance(response, TemplateResponse)
    assert response.status_code == 200
    raw = _issued(response)[0][1]

    body = response.render().content.decode()
    assert raw in body
    assert form.instance.secret_hash not in body


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

    response = key_admin.generate_replacement_keys(request, APIKey.objects.filter(pk=key.pk))

    replacement = APIKey.objects.exclude(pk=key.pk).get()
    assert replacement.profile == profile1
    assert replacement.name == "nightly job"
    assert replacement.key_id != key.key_id
    assert replacement.secret_hash != key.secret_hash
    assert replacement.expires_at is not None

    key.refresh_from_db()
    assert key.is_usable is True

    raw = _issued(response)[0][1]
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


def test_the_csv_export_writes_no_hash(key_admin, profile1, project1):
    """The written bytes, not the configuration that produces them.

    `test_admin_never_exposes_the_hash` asserts secret_hash is in neither
    exportable_fields nor list_display, which is a statement about intent;
    this runs the action that a person actually clicks and reads the file it
    hands back, so a change to how export_model_as_csv resolves a field name
    into a value cannot reintroduce the hash without failing here.
    """

    key, _ = _make_key(profile1, name="exported bot")

    response = export_model_display_as_csv(
        key_admin, _request(method="get"), APIKey.objects.filter(pk=key.pk)
    )

    content = response.content.decode()
    # The export ran and carries the row, so the absence below is the export
    # withholding the hash rather than an empty file.
    assert "exported bot" in content
    assert key.key_id in content
    assert "secret_hash" not in content
    assert key.secret_hash not in content


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


def test_profile_email_is_escaped_in_the_admin_email_link(profile1):
    """The profile changelist and every `profile` autocomplete result render
    `linked_email`, and Profile.email arrives from Auth0 user_info without
    going through full_clean, so markup in the stored value must be escaped
    rather than handed to the browser as HTML."""

    profile1.email = '"><script>alert(1)</script>@example.com'
    profile_admin = ProfileAdmin(Profile, AdminSite())

    rendered = profile_admin.linked_email(profile1)

    assert "<script>" not in rendered
    assert "&lt;script&gt;" in rendered
