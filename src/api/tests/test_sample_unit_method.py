from django.urls import reverse

from api.models import (
    AuditRecord,
    BeltFish,
    BeltInvert,
    CollectRecord,
    ProjectProfile,
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


def test_update_belt_invert_transect_method(db_setup, api_client1, project1, belt_invert1_with_obs):
    belt_invert_id = str(belt_invert1_with_obs.pk)
    url_kwargs = {"project_pk": str(project1.pk), "pk": belt_invert_id}
    detail_url = reverse("beltinverttransectmethod-detail", kwargs=url_kwargs)

    get_response = api_client1.get(detail_url)
    assert get_response.status_code == 200
    data = get_response.json()

    put_response = api_client1.put(detail_url, data, format="json")
    assert put_response.status_code == 200
    put_data = put_response.json()
    assert put_data["id"] == belt_invert_id

    assert (
        put_data["beltinvert_transect"]["len_surveyed"]
        == data["beltinvert_transect"]["len_surveyed"]
    )
    assert put_data["beltinvert_transect"]["depth"] == data["beltinvert_transect"]["depth"]

    assert len(put_data["obs_belt_inverts"]) == 1
    put_obs = put_data["obs_belt_inverts"][0]
    original_obs = data["obs_belt_inverts"][0]
    assert put_obs["invert_attribute"] == original_obs["invert_attribute"]
    assert put_obs["count"] == original_obs["count"]
    assert put_obs["size"] == original_obs["size"]


def test_update_belt_invert_transect_method_cross_project_id_rejected(
    db_setup, api_client2, project2, profile2, project1, belt_invert1
):
    # profile2 is an admin of project2, but belt_invert1 belongs to project1
    ProjectProfile.objects.create(project=project2, profile=profile2, role=ProjectProfile.ADMIN)

    belt_invert_id = str(belt_invert1.pk)
    url_kwargs = {"project_pk": str(project2.pk), "pk": belt_invert_id}
    detail_url = reverse("beltinverttransectmethod-detail", kwargs=url_kwargs)

    response = api_client2.put(detail_url, {"id": belt_invert_id}, format="json")

    assert response.status_code == 404
    # belt_invert1 is untouched and still belongs to project1
    assert BeltInvert.objects.get(id=belt_invert_id).transect.sample_event.site.project_id == (
        project1.pk
    )


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
