import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from api.models import (
    AuditRecord,
    AuthUser,
    BeltFish,
    CollectRecord,
    Observer,
    Profile,
    Revision,
)


def test_sampleunitmethods_list_includes_macroinvertebrate(
    client,
    db_setup,
    project1,
    token1,
    belt_invert1,
):
    url = reverse("sampleunitmethod-list", kwargs={"project_pk": str(project1.pk)})
    response = client.get(
        f"{url}?protocol=macroinvertebrate",
        HTTP_AUTHORIZATION=f"Bearer {token1}",
    )
    data = response.json()

    assert response.status_code == 200
    assert data["count"] == 1

    result = data["results"][0]
    assert result["protocol"] == "macroinvertebrate"
    assert result["sample_date"] is not None
    assert result["site_name"] is not None
    assert result["size"]["width"] is not None
    assert result["size"]["len_surveyed"] is not None


def test_sampleunitmethods_search_and_size_cover_pqt_and_macroinvertebrate(
    db_setup,
    api_client1,
    project1,
    profile1,
    belt_invert1,
    benthic_photo_quadrat_transect1,
    observer_benthic_photo_quadrat_transect1,
):
    # belt_invert1 already has an observer (profile1)
    url = reverse("sampleunitmethod-list", kwargs={"project_pk": str(project1.pk)})
    protocols = "benthicpqt,macroinvertebrate"

    response = api_client1.get(url, {"protocol": protocols, "search": profile1.first_name})
    assert response.status_code == 200
    results = {r["protocol"]: r for r in response.json()["results"]}
    assert set(results) == {"benthicpqt", "macroinvertebrate"}
    assert results["benthicpqt"]["size"] == {
        "len_surveyed": benthic_photo_quadrat_transect1.quadrat_transect.len_surveyed,
        "len_surveyed_units": "m",
    }

    response = api_client1.get(url, {"protocol": protocols, "search": "no-such-observer"})
    assert response.json()["count"] == 0


def test_sampleunitmethods_query_count_independent_of_unnamed_observer_rows(
    db_setup,
    api_client1,
    project1,
    belt_fish1,
    benthic_photo_quadrat_transect1,
    belt_invert1,
    django_assert_max_num_queries,
):
    url = reverse("sampleunitmethod-list", kwargs={"project_pk": str(project1.pk)})
    params = {"protocol": "fishbelt,benthicpqt,macroinvertebrate"}
    email = "unnamedobserver@mermaidcollect.org"
    profile = Profile.objects.create(email=email)
    AuthUser.objects.create(profile=profile, user_id=f"test|{email}")

    Observer.objects.create(transectmethod=belt_fish1, profile=profile)
    with CaptureQueriesContext(connection) as ctx:
        assert api_client1.get(url, params).status_code == 200
    num_queries_1x = len(ctx.captured_queries)

    for tm in (benthic_photo_quadrat_transect1, belt_invert1):
        Observer.objects.create(transectmethod=tm, profile=profile)
    with django_assert_max_num_queries(num_queries_1x):
        response = api_client1.get(url, params)
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 3
    assert all("unnamedobserver" in r["observers"] for r in results)


def _get_latest_proj_revision():
    revision_num = (
        Revision.objects.filter(table_name="project").order_by("-revision_num")[0].revision_num
    )
    return revision_num


def test_edit_benthic_photo_quadrat_transect_method(
    db_setup,
    api_client1,
    project1,
    benthic_photo_quadrat_transect_project,
    benthic_photo_quadrat_transect1,
    profile1,
):
    benthic_photo_quadrat_transect_id = str(benthic_photo_quadrat_transect1.pk)
    url_kwargs = {
        "project_pk": str(project1.pk),
        "pk": benthic_photo_quadrat_transect_id,
    }
    data = {"profile": str(profile1.pk)}
    edit_url = reverse("benthicphotoquadrattransectmethod-edit", kwargs=url_kwargs)

    request = api_client1.put(edit_url, data, format="json")
    response_data = request.json()

    assert request.status_code == 200

    collect_records = CollectRecord.objects.filter(id=response_data["id"])

    assert collect_records.exists()
    assert collect_records[0].data.get("sample_unit_method_id") == benthic_photo_quadrat_transect_id
    assert AuditRecord.objects.filter(
        record_id=benthic_photo_quadrat_transect_id,
        event_type=AuditRecord.EDIT_RECORD_EVENT_TYPE,
        model=benthic_photo_quadrat_transect1.__class__.__name__.lower(),
    ).exists()


def test_edit_belt_fish_transect_method(
    db_setup, api_client1, project1, belt_fish_project, belt_fish1, profile2
):
    base_revision_num = _get_latest_proj_revision()
    belt_fish_id = str(belt_fish1.pk)
    url_kwargs = {"project_pk": str(project1.pk), "pk": belt_fish_id}
    data = {"profile": str(profile2.pk)}
    edit_url = reverse("beltfishtransectmethod-edit", kwargs=url_kwargs)

    request = api_client1.put(edit_url, data, format="json")
    response_data = request.json()

    collect_records = CollectRecord.objects.filter(id=response_data["id"])

    assert request.status_code == 200
    assert collect_records.exists()
    assert collect_records[0].data.get("sample_unit_method_id") == belt_fish_id
    assert AuditRecord.objects.filter(
        record_id=belt_fish_id,
        event_type=AuditRecord.EDIT_RECORD_EVENT_TYPE,
        model=belt_fish1.__class__.__name__.lower(),
    ).exists()

    # project is updated with # of CRs/SUs when SU reverted to CR
    revision_num = _get_latest_proj_revision()
    assert revision_num > base_revision_num


def test_submit_collect_record_v2(
    db_setup, api_client1, project1, collect_record4_with_v2_validation
):
    base_revision_num = _get_latest_proj_revision()
    url_kwargs = {"project_pk": str(project1.pk)}
    edit_url = reverse("collectrecords-submit", kwargs=url_kwargs)

    assert (
        BeltFish.objects.filter(
            id=collect_record4_with_v2_validation.data.get("sample_unit_method_id")
        ).exists()
        is False
    )

    collect_record_id = str(collect_record4_with_v2_validation.pk)
    request = api_client1.post(
        edit_url, data={"version": "2", "ids": [collect_record_id]}, format="json"
    )
    response_data = request.json()

    assert response_data[collect_record_id]["status"] == "ok"
    assert CollectRecord.objects.filter(id=collect_record_id).exists() is False
    assert AuditRecord.objects.filter(
        record_id=collect_record_id,
        event_type=AuditRecord.SUBMIT_RECORD_EVENT_TYPE,
        model=CollectRecord.__name__.lower(),
    ).exists()
    assert BeltFish.objects.filter(
        id=collect_record4_with_v2_validation.data.get("sample_unit_method_id")
    ).exists()

    # project is updated with # of CRs/SUs when CR submitted
    revision_num = _get_latest_proj_revision()
    assert revision_num > base_revision_num


SAMPLE_UNIT_METHODS = [
    ("beltfishtransectmethod", "belt_fish1"),
    ("beltinverttransectmethod", "belt_invert1"),
    ("benthiclittransectmethod", "benthic_lit1"),
    ("benthicpittransectmethod", "benthic_pit1"),
    ("benthicphotoquadrattransectmethod", "benthic_photo_quadrat_transect1"),
    ("bleachingquadratcollectionmethod", "bleaching_quadrat_collection1"),
    ("habitatcomplexitytransectmethod", "habitat_complexity1"),
]


@pytest.mark.parametrize("url_name,fixture_name", SAMPLE_UNIT_METHODS)
def test_direct_write_to_sample_unit_method_not_allowed(
    request, db_setup, api_client1, project1, url_name, fixture_name
):
    # Submitted data only changes via /edit/ -> collect record -> submit.
    instance = request.getfixturevalue(fixture_name)
    model = instance.__class__
    project_pk = str(project1.pk)
    detail_url = reverse(
        f"{url_name}-detail", kwargs={"project_pk": project_pk, "pk": str(instance.pk)}
    )
    list_url = reverse(f"{url_name}-list", kwargs={"project_pk": project_pk})
    data = api_client1.get(detail_url).json()
    updated_on = model.objects.get(pk=instance.pk).updated_on
    count = model.objects.count()

    put_response = api_client1.put(detail_url, data, format="json")
    assert put_response.status_code == 405
    assert "project admin" in put_response.json()["detail"]
    assert "PUT" not in put_response["Allow"]
    assert api_client1.patch(detail_url, data, format="json").status_code == 405
    data.pop("id")
    assert api_client1.post(list_url, data, format="json").status_code == 405

    assert model.objects.get(pk=instance.pk).updated_on == updated_on
    assert model.objects.count() == count


@pytest.mark.parametrize("url_name,fixture_name", SAMPLE_UNIT_METHODS)
def test_delete_sample_unit_method_writes_audit_record(
    request, db_setup, api_client1, project1, profile1, url_name, fixture_name
):
    instance = request.getfixturevalue(fixture_name)
    model = instance.__class__
    url = reverse(
        f"{url_name}-detail", kwargs={"project_pk": str(project1.pk), "pk": str(instance.pk)}
    )

    response = api_client1.delete(url)

    assert response.status_code == 204
    assert not model.objects.filter(pk=instance.pk).exists()
    assert AuditRecord.objects.filter(
        record_id=instance.pk,
        event_type=AuditRecord.DELETE_RECORD_EVENT_TYPE,
        event_by=profile1,
        model=model.__name__.lower(),
    ).exists()


def test_delete_sample_unit_method_denied_writes_no_audit_record(
    db_setup, api_client2, project1, belt_fish1
):
    url = reverse(
        "beltfishtransectmethod-detail",
        kwargs={"project_pk": str(project1.pk), "pk": str(belt_fish1.pk)},
    )

    response = api_client2.delete(url)

    assert response.status_code == 403
    assert BeltFish.objects.filter(pk=belt_fish1.pk).exists()
    assert not AuditRecord.objects.filter(record_id=belt_fish1.pk).exists()


def test_sample_unit_method_detail_does_not_advertise_put(
    db_setup, api_client1, project1, belt_fish1
):
    kwargs = {"project_pk": str(project1.pk), "pk": str(belt_fish1.pk)}
    detail_response = api_client1.options(reverse("beltfishtransectmethod-detail", kwargs=kwargs))
    edit_response = api_client1.options(reverse("beltfishtransectmethod-edit", kwargs=kwargs))

    assert "PUT" not in detail_response["Allow"]
    assert "DELETE" in detail_response["Allow"]
    assert "PUT" not in detail_response.json().get("actions", {})
    assert "PUT" in edit_response["Allow"]


def test_collector_direct_put_points_to_project_admin(db_setup, api_client2, project1, belt_fish1):
    url = reverse(
        "beltfishtransectmethod-detail",
        kwargs={"project_pk": str(project1.pk), "pk": str(belt_fish1.pk)},
    )

    response = api_client2.put(url, {}, format="json")

    assert response.status_code == 405
    assert "project admin" in response.json()["detail"]
    assert "/edit/" not in response.json()["detail"]


def test_delete_sample_unit_method_already_deleted_returns_404(
    db_setup, api_client1, project1, belt_fish1
):
    from unittest import mock

    from api.resources.sampleunitmethods.beltfishmethod import BeltFishMethodView

    url = reverse(
        "beltfishtransectmethod-detail",
        kwargs={"project_pk": str(project1.pk), "pk": str(belt_fish1.pk)},
    )
    stale = BeltFish.objects.get(pk=belt_fish1.pk)
    BeltFish.objects.filter(pk=belt_fish1.pk).delete()  # a concurrent delete won the race

    with mock.patch.object(BeltFishMethodView, "get_object", return_value=stale):
        response = api_client1.delete(url)

    assert response.status_code == 404
    assert not AuditRecord.objects.filter(record_id=belt_fish1.pk).exists()
