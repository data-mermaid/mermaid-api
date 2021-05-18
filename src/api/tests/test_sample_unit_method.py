from django.urls import reverse

from api.models import CollectRecord, AuditRecord


def test_edit_transect_method(db_setup, api_client1, project1, belt_fish_project, belt_fish1, profile2):
    belt_fish_id = str(belt_fish1.pk)
    url_kwargs = {
        "project_pk": str(project1.pk),
        "pk": belt_fish_id        
    }
    data = {
        "profile": str(profile2.pk)
    }
    edit_url = reverse("beltfishtransectmethod-edit", kwargs=url_kwargs)


    request = api_client1.put(edit_url, data, format="json")
    response_data = request.json()

    assert request.status_code == 200
    assert CollectRecord.objects.filter(id=response_data["id"]).exists()
    assert AuditRecord.objects.filter(
        record_id=belt_fish_id,
        event_type=AuditRecord.EDIT_RECORD_EVENT_TYPE,
        model=belt_fish1.__class__.__name__.lower()
    ).exists()


def test_submit_collect_record(db_setup, api_client1, project1, collect_record4):
    url_kwargs = {
        "project_pk": str(project1.pk)       
    }
    edit_url = reverse("collectrecords-submit", kwargs=url_kwargs)

    collect_record_id = str(collect_record4.pk)
    request = api_client1.post(edit_url, data={"ids": [collect_record_id]}, format="json")
    response_data = request.json()

    assert response_data[collect_record_id]["status"] == "ok"
    assert CollectRecord.objects.filter(id=collect_record_id).exists() is False
    assert AuditRecord.objects.filter(
        record_id=collect_record_id,
        event_type=AuditRecord.SUBMIT_RECORD_EVENT_TYPE,
        model=CollectRecord.__name__.lower()
    ).exists()
