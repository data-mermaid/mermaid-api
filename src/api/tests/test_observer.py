from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from api.models import AuthUser, Observer, Profile


def _add_unnamed_observers(start, count, transectmethod):
    for i in range(start, start + count):
        email = f"unnamedobserver{i}@mermaidcollect.org"
        profile = Profile.objects.create(email=email)
        AuthUser.objects.create(profile=profile, user_id=f"test|{email}")
        Observer.objects.create(transectmethod=transectmethod, profile=profile)


def test_observer_list_query_count_independent_of_unnamed_observers(
    db_setup, api_client1, project1, belt_fish1, django_assert_max_num_queries
):
    """Observer.profile_name falls back to Profile.num_account_connections for profiles
    without a first or last name; the observer list must read it from the authusers
    prefetch instead of running one COUNT per observer."""
    url = reverse("observer-list", kwargs={"project_pk": str(project1.pk)})

    _add_unnamed_observers(0, 1, belt_fish1)
    with CaptureQueriesContext(connection) as ctx:
        response = api_client1.get(url)
    assert response.status_code == 200
    assert [o["profile_name"] for o in response.json()["results"]] == ["unnamedobserver0"]
    num_queries_1x = len(ctx.captured_queries)

    _add_unnamed_observers(1, 4, belt_fish1)
    with django_assert_max_num_queries(num_queries_1x):
        response = api_client1.get(url)
    assert response.status_code == 200
    assert sorted(o["profile_name"] for o in response.json()["results"]) == [
        f"unnamedobserver{i}" for i in range(5)
    ]
