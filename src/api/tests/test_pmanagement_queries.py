from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from api.models import Management


def _add_managements(start, count, project, parties):
    for i in range(start, start + count):
        management = Management.objects.create(project=project, name=f"Management {i}")
        management.parties.set(parties)


def test_pmanagement_list_query_count_independent_of_row_count(
    db_setup, api_client1, project1, managment_party1, managment_party2
):
    url = reverse("pmanagement-list", kwargs={"project_pk": str(project1.pk)})
    parties = [managment_party1, managment_party2]

    _add_managements(0, 2, project1, parties)
    with CaptureQueriesContext(connection) as ctx_2:
        response_2 = api_client1.get(url)
    _add_managements(2, 8, project1, parties)
    with CaptureQueriesContext(connection) as ctx_10:
        response_10 = api_client1.get(url)

    assert response_2.status_code == 200
    assert response_10.status_code == 200
    assert response_2.json()["count"] == 2
    assert response_10.json()["count"] == 10
    assert len(ctx_10.captured_queries) == len(ctx_2.captured_queries)

    expected_parties = sorted(str(p.pk) for p in parties)
    for record in response_10.json()["results"]:
        assert sorted(str(p) for p in record["parties"]) == expected_parties
