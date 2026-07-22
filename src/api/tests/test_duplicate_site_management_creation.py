import uuid

from django.urls import reverse


def _site_payload(project, country, reef_type, reef_zone, exposure, name, lon, lat):
    return {
        "id": str(uuid.uuid4()),
        "name": name,
        "project": str(project.pk),
        "country": str(country.pk),
        "reef_type": str(reef_type.pk),
        "reef_zone": str(reef_zone.pk),
        "exposure": str(exposure.pk),
        "location": {"type": "Point", "coordinates": [lon, lat]},
    }


def _management_payload(project, name):
    return {"id": str(uuid.uuid4()), "name": name, "project": str(project.pk)}


# PSiteSerializer.create() -- site1 ("Site 1" at (1, 1)) gets submitted data from
# benthic_transect1.


def test_psite_create_rejects_nearby_similarly_named_site_with_data(
    api_client1,
    project1,
    site1,
    benthic_transect1,
    country1,
    reef_type1,
    reef_zone1,
    reef_exposure1,
):
    url = reverse("psite-list", kwargs=dict(project_pk=project1.pk))
    payload = _site_payload(
        project1, country1, reef_type1, reef_zone1, reef_exposure1, "Site 1 ", 1.0001, 1.0001
    )
    resp = api_client1.post(url, payload, format="json")

    assert resp.status_code == 400
    assert resp.json()["duplicate"]["code"] == "not_unique_site"
    assert str(site1.pk) in resp.json()["duplicate"]["matches"]


def test_psite_create_override_flag_allows_creation_anyway(
    api_client1,
    project1,
    site1,
    benthic_transect1,
    country1,
    reef_type1,
    reef_zone1,
    reef_exposure1,
):
    url = reverse("psite-list", kwargs=dict(project_pk=project1.pk))
    payload = _site_payload(
        project1, country1, reef_type1, reef_zone1, reef_exposure1, "Site 1 ", 1.0001, 1.0001
    )
    payload["ignore_duplicate_warning"] = True
    resp = api_client1.post(url, payload, format="json")

    assert resp.status_code == 201


def test_psite_update_does_not_run_duplicate_check(api_client1, project1, site1):
    # The check only applies to creation (self.instance is None): updating an
    # existing site must not trip it, even though site1 obviously "matches
    # itself" by name/location.
    url = reverse("psite-detail", kwargs=dict(project_pk=project1.pk, pk=site1.pk))
    resp = api_client1.get(url, format="json")
    payload = resp.json()
    payload["notes"] = "updated"

    resp = api_client1.put(url, payload, format="json")

    assert resp.status_code == 200


def test_psite_create_allows_dissimilar_name_nearby(
    api_client1,
    project1,
    site1,
    benthic_transect1,
    country1,
    reef_type1,
    reef_zone1,
    reef_exposure1,
):
    url = reverse("psite-list", kwargs=dict(project_pk=project1.pk))
    payload = _site_payload(
        project1,
        country1,
        reef_type1,
        reef_zone1,
        reef_exposure1,
        "Completely different station",
        1.0001,
        1.0001,
    )
    resp = api_client1.post(url, payload, format="json")

    assert resp.status_code == 201


def test_psite_create_allows_similar_name_far_away(
    api_client1,
    project1,
    site1,
    benthic_transect1,
    country1,
    reef_type1,
    reef_zone1,
    reef_exposure1,
):
    url = reverse("psite-list", kwargs=dict(project_pk=project1.pk))
    payload = _site_payload(
        project1, country1, reef_type1, reef_zone1, reef_exposure1, "Site 1 ", -50, -50
    )
    resp = api_client1.post(url, payload, format="json")

    assert resp.status_code == 201


def test_psite_create_allows_similar_name_nearby_without_submitted_data(
    api_client1, project1, site2, country1, reef_type1, reef_zone1, reef_exposure1
):
    # site2 ("Site 2" at ~(1.01, 1.01)) has no submitted sample unit.
    url = reverse("psite-list", kwargs=dict(project_pk=project1.pk))
    payload = _site_payload(
        project1, country1, reef_type1, reef_zone1, reef_exposure1, "Site 2 ", 1.0101, 1.0101
    )
    resp = api_client1.post(url, payload, format="json")

    assert resp.status_code == 201


# PManagementSerializer.create()


def test_pmanagement_create_rejects_normalized_name_match_with_data(
    api_client1, project1, management1, benthic_transect1
):
    url = reverse("pmanagement-list", kwargs=dict(project_pk=project1.pk))
    payload = _management_payload(project1, "management-1")

    resp = api_client1.post(url, payload, format="json")

    assert resp.status_code == 400
    assert resp.json()["duplicate"]["code"] == "similar_name"
    assert str(management1.pk) in resp.json()["duplicate"]["matches"]


def test_pmanagement_create_rejects_name_match_with_only_macroinvertebrate_data(
    api_client1, project1, management1, invert_belt_transect1
):
    # management1 has data only via a macroinvertebrate sample unit (no
    # benthic/fish/quadrat rows) -- the "has submitted data" precondition
    # must still recognize it, the same way it would for any other protocol.
    url = reverse("pmanagement-list", kwargs=dict(project_pk=project1.pk))
    payload = _management_payload(project1, "management-1")

    resp = api_client1.post(url, payload, format="json")

    assert resp.status_code == 400
    assert resp.json()["duplicate"]["code"] == "similar_name"


def test_pmanagement_create_override_flag_allows_creation_anyway(
    api_client1, project1, management1, benthic_transect1
):
    url = reverse("pmanagement-list", kwargs=dict(project_pk=project1.pk))
    payload = _management_payload(project1, "management-1")
    payload["ignore_duplicate_warning"] = True

    resp = api_client1.post(url, payload, format="json")

    assert resp.status_code == 201


def test_pmanagement_update_does_not_run_duplicate_check(api_client1, project1, management1):
    # The check only applies to creation (self.instance is None): updating an
    # existing management regime must not trip it, even though management1
    # obviously "matches itself" by name.
    url = reverse("pmanagement-detail", kwargs=dict(project_pk=project1.pk, pk=management1.pk))
    resp = api_client1.get(url, format="json")
    payload = resp.json()
    payload["notes"] = "updated"

    resp = api_client1.put(url, payload, format="json")

    assert resp.status_code == 200


def test_pmanagement_create_allows_distinct_name(
    api_client1, project1, management1, benthic_transect1
):
    url = reverse("pmanagement-list", kwargs=dict(project_pk=project1.pk))
    payload = _management_payload(project1, "A totally different MR")

    resp = api_client1.post(url, payload, format="json")

    assert resp.status_code == 201


def test_pmanagement_create_allows_name_match_without_submitted_data(
    api_client1, project1, management2
):
    # management2 has no submitted sample unit.
    url = reverse("pmanagement-list", kwargs=dict(project_pk=project1.pk))
    payload = _management_payload(project1, "management 2")

    resp = api_client1.post(url, payload, format="json")

    assert resp.status_code == 201


# Note: create_project's bulk sites/managements array (api/resources/project.py) uses
# SiteSerializer/ManagementSerializer (site.py/management.py), which deliberately do NOT
# carry SiteDuplicateCheckMixin/ManagementDuplicateCheckMixin -- that endpoint always
# copies into a brand-new project, so the check's "already has submitted data"
# precondition can never be met there; the mixin would just be dead weight. Nothing to
# test here since that code path is untouched by this feature.


# Sync push (/v1/push/, api/resources/sync/) uses the same PSiteSerializer/
# PManagementSerializer as the normal REST endpoints, but through a hand-rolled
# is_valid()/apply_changes() flow with its own exception handling -- this is the path
# that originally motivated moving the check into validate() rather than create().


def test_sync_push_site_duplicate_returns_400_not_500(
    api_client1,
    project1,
    site1,
    benthic_transect1,
    country1,
    reef_type1,
    reef_zone1,
    reef_exposure1,
):
    payload = _site_payload(
        project1, country1, reef_type1, reef_zone1, reef_exposure1, "Site 1 ", 1.0001, 1.0001
    )
    resp = api_client1.post("/v1/push/", {"project_sites": [payload]}, format="json")

    assert resp.status_code == 200
    result = resp.json()["project_sites"][0]
    assert result["status_code"] == 400
    assert result["data"]["duplicate"]["code"] == "not_unique_site"


def test_sync_push_site_duplicate_override_flag_allows_creation(
    api_client1,
    project1,
    site1,
    benthic_transect1,
    country1,
    reef_type1,
    reef_zone1,
    reef_exposure1,
):
    payload = _site_payload(
        project1, country1, reef_type1, reef_zone1, reef_exposure1, "Site 1 ", 1.0001, 1.0001
    )
    payload["ignore_duplicate_warning"] = True
    resp = api_client1.post("/v1/push/", {"project_sites": [payload]}, format="json")

    assert resp.status_code == 200
    result = resp.json()["project_sites"][0]
    assert result["status_code"] == 201


def test_sync_push_management_duplicate_returns_400_not_500(
    api_client1, project1, management1, benthic_transect1
):
    payload = _management_payload(project1, "management-1")
    resp = api_client1.post("/v1/push/", {"project_managements": [payload]}, format="json")

    assert resp.status_code == 200
    result = resp.json()["project_managements"][0]
    assert result["status_code"] == 400
    assert result["data"]["duplicate"]["code"] == "similar_name"


def test_sync_push_management_duplicate_override_flag_allows_creation(
    api_client1, project1, management1, benthic_transect1
):
    payload = _management_payload(project1, "management-1")
    payload["ignore_duplicate_warning"] = True
    resp = api_client1.post("/v1/push/", {"project_managements": [payload]}, format="json")

    assert resp.status_code == 200
    result = resp.json()["project_managements"][0]
    assert result["status_code"] == 201
