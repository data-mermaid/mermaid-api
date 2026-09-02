"""C3: a key is scoped to a project list, so a stolen key reaches those
projects and nothing else - even where the profile behind it is a member of
more."""

import uuid
from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.core.cache import cache
from django.http import QueryDict
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from api.mocks import MockRequest
from api.models import FISHBELT_PROTOCOL, APIKey, Project, ProjectProfile, Site
from api.permissions import API_KEY_SCOPE_CACHE_ATTR, api_key_in_scope
from api.reports.summary_report import PROJECT_MEMBER, get_project_protocol_viewable_level
from api.resources.images import AllImagesPermission
from api.resources.sync.utils import create_view_request
from api.utils.apikeys import generate_api_key


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


def _make_key(profile, projects, name="scoped bot"):
    key_id, secret_hash, raw = generate_api_key()
    key = APIKey.objects.create(
        profile=profile,
        name=name,
        key_id=key_id,
        secret_hash=secret_hash,
        expires_at=timezone.now() + timedelta(days=365),
    )
    key.projects.set(projects)
    return key, raw


def _client(raw):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"ApiKey {raw}")
    return client


@pytest.fixture
def profile1_both_projects(project_profile1, project1, project2, profile1):
    """profile1 is ADMIN on project1 (project_profile1) and on project2, so
    membership alone would reach both."""
    ProjectProfile.objects.create(project=project2, profile=profile1, role=ProjectProfile.ADMIN)
    return profile1


@pytest.fixture
def project1_private_policies(project1):
    project1.data_policy_beltfish = Project.PRIVATE
    project1.data_policy_benthicpit = Project.PRIVATE
    project1.save()


@pytest.fixture
def key_client_project1(profile1_both_projects, project1):
    _, raw = _make_key(profile1_both_projects, [project1])
    return _client(raw)


def test_scoped_project_is_reachable(db_setup, key_client_project1, project1):
    url = reverse("psite-list", kwargs=dict(project_pk=project1.pk))
    assert key_client_project1.get(url, format="json").status_code == 200


def test_unscoped_project_is_denied(db_setup, key_client_project1, project2):
    """profile1 is an ADMIN of project2, but the key is not scoped to it."""

    url = reverse("psite-list", kwargs=dict(project_pk=project2.pk))
    assert key_client_project1.get(url, format="json").status_code == 403


def test_unscoped_project_write_is_denied(db_setup, key_client_project1, project2, profile1):
    url = reverse("collectrecords-list", args=[str(project2.pk)])
    data = {
        "id": str(uuid.uuid4()),
        "data": {},
        "project": str(project2.pk),
        "profile": str(profile1.pk),
    }
    assert key_client_project1.post(url, data, format="json").status_code == 403


def test_jwt_client_still_reaches_both_projects(
    db_setup, api_client1, project1, project2, profile1
):
    """The scope check must not touch a request that no key authenticated."""

    ProjectProfile.objects.create(project=project2, profile=profile1, role=ProjectProfile.ADMIN)
    for project in (project1, project2):
        url = reverse("psite-list", kwargs=dict(project_pk=project.pk))
        assert api_client1.get(url, format="json").status_code == 200


def test_collector_profile_key_can_write_on_a_scoped_project(
    db_setup, project1, profile2, project_profile2
):
    """The key carries the profile's role: project_profile2 is a COLLECTOR on
    project1, so the key writes there."""

    _, raw = _make_key(profile2, [project1])
    url = reverse("collectrecords-list", args=[str(project1.pk)])
    data = {
        "id": str(uuid.uuid4()),
        "data": {},
        "project": str(project1.pk),
        "profile": str(profile2.pk),
    }
    assert _client(raw).post(url, data, format="json").status_code == 201


def _site_payload(project, country, reef_type, reef_zone, exposure):
    return {
        "id": str(uuid.uuid4()),
        "name": "Bot site",
        "project": str(project.pk),
        "country": str(country.pk),
        "reef_type": str(reef_type.pk),
        "reef_zone": str(reef_zone.pk),
        "exposure": str(exposure.pk),
        "location": {"type": "Point", "coordinates": [1.5, 1.5]},
    }


def test_readonly_profile_key_cannot_write_on_a_scoped_project(
    db_setup, project1, profile3, country1, reef_type1, reef_zone1, reef_exposure1
):
    """Scope decides which projects a key reaches; the profile's role decides
    what it may do there. A READONLY member's key reads and nothing more."""

    ProjectProfile.objects.create(project=project1, profile=profile3, role=ProjectProfile.READONLY)
    _, raw = _make_key(profile3, [project1], name="readonly bot")
    client = _client(raw)
    url = reverse("psite-list", kwargs=dict(project_pk=project1.pk))

    assert client.get(url, format="json").status_code == 200

    payload = _site_payload(project1, country1, reef_type1, reef_zone1, reef_exposure1)
    assert client.post(url, payload, format="json").status_code == 403


def test_locked_project_key_cannot_write(
    db_setup,
    project1,
    profile2,
    project_profile2,
    country1,
    reef_type1,
    reef_zone1,
    reef_exposure1,
):
    """A LOCKED project downgrades COLLECTORs to read-only, and a key inherits
    that: the same POST that a COLLECTOR's key makes on an open project is now
    a 403."""

    _, raw = _make_key(profile2, [project1])
    url = reverse("psite-list", kwargs=dict(project_pk=project1.pk))
    payload = _site_payload(project1, country1, reef_type1, reef_zone1, reef_exposure1)

    assert _client(raw).post(url, payload, format="json").status_code == 201

    project1.status = Project.LOCKED
    project1.save()

    payload = _site_payload(project1, country1, reef_type1, reef_zone1, reef_exposure1)
    assert _client(raw).post(url, payload, format="json").status_code == 403


def test_admin_profile_key_can_do_admin_actions_on_a_scoped_project(
    db_setup, base_project, project1, profile1, project_profile1
):
    _, raw = _make_key(profile1, [project1])
    url = reverse("project-add-profile", kwargs=dict(pk=project1.pk))
    response = _client(raw).post(
        url, {"email": "bot-added@test.com", "role": ProjectProfile.COLLECTOR}, format="json"
    )
    assert response.status_code == 200


def test_project_list_returns_only_scoped_projects(
    db_setup, key_client_project1, project1, project2
):
    response = key_client_project1.get(reverse("project-list"), format="json")
    assert response.status_code == 200
    ids = {r["id"] for r in response.json()["results"]}
    assert ids == {str(project1.pk)}


def test_project_list_showall_is_still_scoped(db_setup, key_client_project1, project1, project2):
    """showall hands an unscoped caller every project; a key must not get one
    it is not scoped to."""

    response = key_client_project1.get(f"{reverse('project-list')}?showall", format="json")
    assert response.status_code == 200
    ids = {r["id"] for r in response.json()["results"]}
    assert ids == {str(project1.pk)}


def test_project_detail_out_of_scope_is_denied(db_setup, key_client_project1, project2):
    url = reverse("project-detail", kwargs=dict(pk=project2.pk))
    assert key_client_project1.get(url, format="json").status_code == 404


def test_me_still_works_for_a_key(db_setup, key_client_project1, profile1):
    """A non-project endpoint is unaffected by scope."""

    response = key_client_project1.get(reverse("me-list"), format="json")
    assert response.status_code == 200
    assert response.json()["id"] == str(profile1.pk)


def test_scope_lookup_is_memoized_per_request(
    db_setup, profile1, project1, project_profile1, django_assert_num_queries
):
    """Permission classes re-check the same project several times per request,
    so the scope lookup is cached alongside get_project/get_project_profile."""

    key, _ = _make_key(profile1, [project1])

    class _Req:
        auth = key

    request = _Req()
    assert api_key_in_scope(request, project1.pk) is True
    assert getattr(request, API_KEY_SCOPE_CACHE_ATTR) == {project1.pk: True}

    with django_assert_num_queries(0):
        assert api_key_in_scope(request, project1.pk) is True


def test_scope_check_ignores_a_request_without_a_key(db_setup, project1):
    assert api_key_in_scope(None, project1.pk) is True

    class _Req:
        auth = "a-jwt-string"

    assert api_key_in_scope(_Req(), project1.pk) is True


def test_view_request_carries_the_api_key(db_setup, profile1, project1):
    """Sync builds a derived request per record; scope has to survive that."""

    key, _ = _make_key(profile1, [project1])

    class _Req:
        auth = key
        user = None
        method = "GET"
        headers = {}
        META = {}
        authenticators = ()
        successful_authenticator = None

    vw_request = create_view_request(_Req())
    assert vw_request.auth is key


def test_write_is_attributed_to_the_key_s_profile(
    db_setup,
    project1,
    profile2,
    project_profile2,
    country1,
    reef_type1,
    reef_zone1,
    reef_exposure1,
):
    """A key request carries no JWT, so updated_by has to come from the
    profile the key resolved to rather than the Authorization header."""

    _, raw = _make_key(profile2, [project1])
    url = reverse("psite-list", kwargs=dict(project_pk=project1.pk))
    response = _client(raw).post(
        url,
        {
            "id": str(uuid.uuid4()),
            "name": "Bot site",
            "project": str(project1.pk),
            "country": str(country1.pk),
            "reef_type": str(reef_type1.pk),
            "reef_zone": str(reef_zone1.pk),
            "exposure": str(reef_exposure1.pk),
            "location": {"type": "Point", "coordinates": [1.5, 1.5]},
        },
        format="json",
    )
    assert response.status_code == 201
    assert Site.objects.get(pk=response.json()["id"]).updated_by == profile2


def test_all_images_permission_respects_scope(
    db_setup, profile1, project1, project2, project_profile1
):
    """AllImagesViewSet spans projects and reads membership directly, so it
    repeats the scope check that get_project_profile does elsewhere."""

    ProjectProfile.objects.create(project=project2, profile=profile1, role=ProjectProfile.ADMIN)
    permission = AllImagesPermission()

    class _Obj:
        project = project1

    def _request(key):
        return SimpleNamespace(auth=key, user=SimpleNamespace(profile=profile1), method="GET")

    in_scope, _ = _make_key(profile1, [project1], name="in scope")
    out_of_scope, _ = _make_key(profile1, [project2], name="out of scope")

    assert permission.has_object_permission(_request(in_scope), None, _Obj()) is True
    assert permission.has_object_permission(_request(out_of_scope), None, _Obj()) is False


def test_summary_sample_events_restricted_data_needs_scope(
    db_setup,
    project1_private_policies,
    project1,
    project2,
    profile1,
    project_profile1,
    sample_event1,
    belt_fish_project,
    benthic_pit_project,
    obs_belt_fish1_1_biomass,
    obs_belt_fish1_2_biomass,
    obs_belt_fish1_3_biomass,
    obs_benthic_pit1_3,
    update_summary_cache,
):
    """profile1 is a member of project1, but a key scoped to project2 sees
    project1 only at the public level - member-only fields stay hidden."""

    _, raw = _make_key(profile1, [project2])
    response = _client(raw).get(reverse("projectsummarysampleevents-list"), None, format="json")

    assert response.status_code == 200
    results = response.json()["results"]
    project1_result = next(r for r in results if r["project_id"] == str(project1.pk))
    record = next(
        r for r in project1_result["records"] if r["sample_event_id"] == str(sample_event1.pk)
    )
    assert "biomass_kgha_avg" not in record["protocols"]["beltfish"]
    assert "percent_cover_benthic_category_avg" not in record["protocols"]["benthicpit"]


def test_report_viewable_level_respects_scope(
    db_setup, profile1, project1, project2, project_profile1
):
    """Reports span projects and decide member-level visibility themselves, so
    the key's scope has to reach that decision too."""

    ProjectProfile.objects.create(project=project2, profile=profile1, role=ProjectProfile.ADMIN)
    key, _ = _make_key(profile1, [project1])
    request = SimpleNamespace(auth=key, user=SimpleNamespace(profile=profile1))

    levels = get_project_protocol_viewable_level(
        request, FISHBELT_PROTOCOL, [project1.pk, project2.pk]
    )

    assert levels[str(project1.pk)] == PROJECT_MEMBER
    assert levels[str(project2.pk)] == project2.data_policy_beltfish


def test_mock_request_keeps_the_api_key(db_setup, profile1, project1):
    """Background reports are handed a MockRequest built from the real one."""

    key, _ = _make_key(profile1, [project1])
    stub = SimpleNamespace(
        user=SimpleNamespace(profile=profile1),
        GET=QueryDict(),
        POST=QueryDict(),
        data={},
        query_params=QueryDict(),
        META={},
        auth=key,
    )

    assert MockRequest.load_request(stub).auth is key
