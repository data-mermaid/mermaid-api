import warnings

from django.core.paginator import UnorderedObjectListWarning
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from api.models import AuthUser, Observer, Profile, ProjectProfile


def _add_unnamed_profile(email):
    profile = Profile.objects.create(email=email)
    AuthUser.objects.create(profile=profile, user_id=f"test|{email}")
    return profile


def _add_observers(profile, transectmethods):
    for tm in transectmethods:
        Observer.objects.create(transectmethod=tm, profile=profile)


def test_observer_list_query_count_independent_of_unnamed_observer_rows(
    db_setup,
    api_client1,
    project1,
    belt_fish1,
    benthic_photo_quadrat_transect1,
    belt_invert1,
    django_assert_max_num_queries,
):
    """Observer.profile_name falls back to Profile.num_account_connections (a COUNT) for
    profiles without a first or last name; it must run once per profile, not per observer."""
    url = reverse("observer-list", kwargs={"project_pk": str(project1.pk)})
    profile = _add_unnamed_profile("unnamedobserver@mermaidcollect.org")

    _add_observers(profile, [belt_fish1])
    with CaptureQueriesContext(connection) as ctx:
        response = api_client1.get(url)
    assert response.status_code == 200
    num_queries_1x = len(ctx.captured_queries)

    _add_observers(profile, [benthic_photo_quadrat_transect1, belt_invert1])
    with django_assert_max_num_queries(num_queries_1x):
        response = api_client1.get(url)
    assert response.status_code == 200
    names = [
        o["profile_name"] for o in response.json()["results"] if o["profile"] == str(profile.pk)
    ]
    assert names == ["unnamedobserver"] * 3


def test_observer_list_is_ordered(db_setup, api_client1, project1, belt_fish1):
    for rank in (3, 1, 2):
        profile = Profile.objects.create(email=f"rank{rank}@mermaidcollect.org")
        Observer.objects.create(transectmethod=belt_fish1, profile=profile, rank=rank)
    url = reverse("observer-list", kwargs={"project_pk": str(project1.pk)})

    with warnings.catch_warnings():
        warnings.simplefilter("error", UnorderedObjectListWarning)
        response = api_client1.get(url)

    assert response.status_code == 200
    assert [o["rank"] for o in response.json()["results"]] == [1, 2, 3]


def test_observer_list_includes_every_protocol(
    db_setup,
    api_client1,
    project1,
    project2,
    profile1,
    belt_fish1,
    benthic_photo_quadrat_transect1,
    belt_invert1,
):
    # belt_invert1 already has an observer (profile1)
    Observer.objects.create(transectmethod=belt_fish1, profile=profile1)
    pqt_observer = Observer.objects.create(
        transectmethod=benthic_photo_quadrat_transect1, profile=profile1
    )
    url = reverse("observer-list", kwargs={"project_pk": str(project1.pk)})

    response = api_client1.get(url)
    assert response.status_code == 200
    assert {o["transectmethod"] for o in response.json()["results"]} == {
        str(belt_fish1.pk),
        str(benthic_photo_quadrat_transect1.pk),
        str(belt_invert1.pk),
    }

    detail_url = reverse(
        "observer-detail", kwargs={"project_pk": str(project1.pk), "pk": str(pqt_observer.pk)}
    )
    assert api_client1.get(detail_url).status_code == 200

    # another project sees none of project1's observers
    ProjectProfile.objects.create(project=project2, profile=profile1, role=ProjectProfile.ADMIN)
    url = reverse("observer-list", kwargs={"project_pk": str(project2.pk)})
    response = api_client1.get(url)
    assert response.status_code == 200
    assert response.json()["results"] == []
