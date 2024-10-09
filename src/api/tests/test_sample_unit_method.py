from django.urls import reverse

from api.models import AuditRecord, BeltFish, CollectRecord, Revision


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
