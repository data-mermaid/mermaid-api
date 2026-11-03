import json

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework.utils.encoders import JSONEncoder

from api.mocks import MockRequest
from api.models import (
    SUPERUSER_APPROVED,
    AuthUser,
    BeltFish,
    BenthicAttribute,
    CollectRecord,
    FishBeltTransect,
    FishSpecies,
    InvertClass,
    InvertFamily,
    InvertGenus,
    InvertGroupOfInterest,
    InvertOrder,
    InvertSpecies,
    Management,
    ObsBeltFish,
    Observer,
    Profile,
    Project,
    ProjectProfile,
    SampleEvent,
    Site,
    Tag,
)
from api.resources.benthic_attribute import BenthicAttributeViewSet
from api.resources.fish_species import FishSpeciesViewSet
from api.resources.invert_attribute import InvertAttributeViewSet
from api.resources.project import ProjectViewSet
from api.resources.project_profile import ProjectProfileViewSet
from api.resources.sampleunitmethods.beltfishmethod import BeltFishMethodSerializer
from api.resources.sync.pull import get_serialized_records
from api.utils.project import suggested_citation

REVISION_KEYS = ("_last_revision_num", "_modified", "_deleted")


def _add_invert_taxa(start, count):
    for i in range(start, start + count):
        goi = InvertGroupOfInterest.objects.create(name=f"GoI {i}", status=SUPERUSER_APPROVED)
        invert_class = InvertClass.objects.create(name=f"Class {i}", status=SUPERUSER_APPROVED)
        order = InvertOrder.objects.create(
            name=f"Order {i}", invert_class=invert_class, status=SUPERUSER_APPROVED
        )
        family = InvertFamily.objects.create(
            name=f"Family {i}", order=order, status=SUPERUSER_APPROVED
        )
        genus = InvertGenus.objects.create(
            name=f"Genus {i}", family=family, group_of_interest=goi, status=SUPERUSER_APPROVED
        )
        InvertSpecies.objects.create(
            name=f"species {i}", genus=genus, max_length=10, status=SUPERUSER_APPROVED
        )


def _add_fish_species(start, count, genus, regions):
    for i in range(start, start + count):
        species = FishSpecies.objects.create(
            name=f"Pull Species {i}", genus=genus, status=SUPERUSER_APPROVED
        )
        species.regions.set(regions)


def _add_benthic_attributes(start, count, regions):
    for i in range(start, start + count):
        attribute = BenthicAttribute.objects.create(
            name=f"Pull Benthic {i}", status=SUPERUSER_APPROVED
        )
        attribute.regions.set(regions)


def _add_projects(start, count, profile, other_profile, site, sample_date):
    for i in range(start, start + count):
        project = Project.objects.create(name=f"Pull Project {i}", status=Project.OPEN)
        for member in (profile, other_profile):
            ProjectProfile.objects.create(
                project=project, profile=member, role=ProjectProfile.ADMIN
            )
        new_site = Site.objects.create(
            project=project,
            name=f"Pull Site {i}",
            location=site.location,
            country=site.country,
            reef_type=site.reef_type,
            exposure=site.exposure,
            reef_zone=site.reef_zone,
        )
        management = Management.objects.create(
            project=project, name=f"Pull Management {i}", est_year=2000
        )
        SampleEvent.objects.create(site=new_site, management=management, sample_date=sample_date)
        project.tags.add(Tag.objects.create(name=f"Pull Org {i}"))
        CollectRecord.objects.create(project=project, profile=profile, data={})


def _add_members(start, count, project):
    for i in range(start, start + count):
        email = f"pull-member{i}@mermaidcollect.org"
        profile = Profile.objects.create(email=email, first_name=f"First{i}", last_name=f"Last{i}")
        AuthUser.objects.create(profile=profile, user_id=f"test|{email}")
        ProjectProfile.objects.create(
            project=project, profile=profile, role=ProjectProfile.COLLECTOR
        )
        CollectRecord.objects.create(project=project, profile=profile, data={})


def _clear_invert_max_length_cache():
    # InvertMaxLengthMixin caches per class for 30s; clear it so each pull
    # does the same queries and sees rows added since the last one.
    for cls in (InvertClass, InvertOrder, InvertFamily, InvertGenus):
        cls.species_agg = None


def _pull(viewset_class, profile, params=None):
    _clear_invert_max_length_cache()
    viewset = viewset_class(request=MockRequest(profile=profile))
    params = {"revision_num": None, **(params or {})}
    with CaptureQueriesContext(connection) as ctx:
        result = get_serialized_records(viewset, str(profile.pk), params)
    return result, len(ctx.captured_queries)


def _as_json(data):
    return json.loads(json.dumps(data, cls=JSONEncoder))


@pytest.fixture
def pull_sources(
    fish_genus1,
    region1,
    region2,
    profile1,
    profile2,
    project1,
    project_profile1,
    site1,
    sample_date1,
):
    # source type: (viewset, add_rows(start, count), pull params)
    # No invert_species: its pull is empty by design (clients pull invert_attributes).
    return {
        "invert_attributes": (InvertAttributeViewSet, _add_invert_taxa, {}),
        "fish_species": (
            FishSpeciesViewSet,
            lambda start, count: _add_fish_species(start, count, fish_genus1, [region1, region2]),
            {},
        ),
        "benthic_attributes": (
            BenthicAttributeViewSet,
            lambda start, count: _add_benthic_attributes(start, count, [region1, region2]),
            {},
        ),
        "projects": (
            ProjectViewSet,
            lambda start, count: _add_projects(
                start, count, profile1, profile2, site1, sample_date1
            ),
            {},
        ),
        "project_profiles": (
            ProjectProfileViewSet,
            lambda start, count: _add_members(start, count, project1),
            {"project": str(project1.pk)},
        ),
    }


PULL_SOURCE_TYPES = [
    "invert_attributes",
    "fish_species",
    "benthic_attributes",
    "projects",
    "project_profiles",
]


@pytest.mark.parametrize("source_type", PULL_SOURCE_TYPES)
def test_pull_query_count_independent_of_row_count(db_setup, profile1, pull_sources, source_type):
    viewset_class, add_rows, params = pull_sources[source_type]

    add_rows(0, 2)
    result_1x, queries_1x = _pull(viewset_class, profile1, params)
    add_rows(2, 4)
    result_3x, queries_3x = _pull(viewset_class, profile1, params)

    assert len(result_3x["updates"]) > len(result_1x["updates"])
    assert queries_3x == queries_1x


@pytest.mark.parametrize("source_type", PULL_SOURCE_TYPES)
def test_pull_serializes_same_as_queryset(db_setup, profile1, pull_sources, source_type):
    # Pull serializes rows from a raw query; the list endpoint serializes the
    # viewset's queryset. The records must come out the same.
    viewset_class, add_rows, params = pull_sources[source_type]
    add_rows(0, 3)

    result, _ = _pull(viewset_class, profile1, params)
    pulled = {
        rec["id"]: {k: v for k, v in rec.items() if k not in REVISION_KEYS}
        for rec in _as_json(result["updates"])
    }

    _clear_invert_max_length_cache()
    viewset = viewset_class(request=MockRequest(profile=profile1))
    request = MockRequest(query_params={"show_hidden": "true"}, GET={"show_hidden": "true"})
    queryset = viewset.get_queryset()
    if "project" in params:
        queryset = queryset.filter(project=params["project"])
    expected = viewset.serializer_class(queryset, many=True, context={"request": request}).data
    expected = {rec["id"]: rec for rec in _as_json(expected)}

    assert pulled
    assert pulled == expected


def _add_belt_fishes(start, count, transect, profile, fish_species):
    for i in range(start, start + count):
        new_transect = FishBeltTransect.objects.create(
            sample_event=transect.sample_event,
            current=transect.current,
            reef_slope=transect.reef_slope,
            relative_depth=transect.relative_depth,
            size_bin=transect.size_bin,
            tide=transect.tide,
            visibility=transect.visibility,
            width=transect.width,
            depth=transect.depth,
            len_surveyed=transect.len_surveyed,
            sample_time=transect.sample_time,
            number=100 + i,
        )
        belt_fish = BeltFish.objects.create(transect=new_transect)
        Observer.objects.create(transectmethod=belt_fish, profile=profile)
        for species in fish_species:
            ObsBeltFish.objects.create(
                beltfish=belt_fish, fish_attribute=species, size=10.0, count=2
            )


def test_beltfish_method_list_query_count_independent_of_row_count(
    db_setup, api_client1, project1, profile1, fishbelt_transect1, fish_species1, fish_species2
):
    url = reverse("beltfishtransectmethod-list", kwargs={"project_pk": str(project1.pk)})
    species = [fish_species1, fish_species2]

    _add_belt_fishes(0, 2, fishbelt_transect1, profile1, species)
    with CaptureQueriesContext(connection) as ctx_1x:
        response_1x = api_client1.get(url)
    _add_belt_fishes(2, 4, fishbelt_transect1, profile1, species)
    with CaptureQueriesContext(connection) as ctx_3x:
        response_3x = api_client1.get(url)

    assert response_1x.json()["count"] == 2
    assert response_3x.json()["count"] == 6
    assert len(ctx_3x.captured_queries) == len(ctx_1x.captured_queries)

    # Same records as serializing without the prefetches.
    unprefetched = BeltFishMethodSerializer(
        BeltFish.objects.filter(transect__sample_event__site__project=project1).order_by(
            "updated_on", "id"
        ),
        many=True,
        context={"request": MockRequest(query_params={}, GET={})},
    ).data
    assert response_3x.json()["results"] == _as_json(unprefetched)


def test_fields_serializer_cache_is_per_serializer(db_setup, api_client1, project1, site1):
    # `?fields=` serializers are cached on BaseApiViewSet, shared by every viewset.
    sites_url = reverse("psite-list", kwargs={"project_pk": str(project1.pk)})
    projects_url = reverse("project-list")

    response = api_client1.get(projects_url, {"fields": "id,name,status"})
    assert response.status_code == 200

    # Same field names on another viewset must use that viewset's serializer.
    response = api_client1.get(sites_url, {"fields": "id,name"})
    assert response.status_code == 200
    assert response.json()["results"] == [{"id": str(site1.pk), "name": site1.name}]

    # `status` isn't a Site field; a cached Project serializer must not skip validation.
    response = api_client1.get(sites_url, {"fields": "id,name,status"})
    assert response.status_code == 400
    assert "fields" in response.json()


def test_project_citation_from_annotation_matches_query(
    db_setup, profile1, profile2, site1, sample_date1
):
    # ProjectViewSet annotates latest_sample_date and prefetches profiles_by_name
    # for the citation; the result must match the per-project queries.
    _add_projects(0, 2, profile1, profile2, site1, sample_date1)
    viewset = ProjectViewSet(request=MockRequest(profile=profile1))
    projects = list(viewset.get_queryset())

    assert projects
    for project in projects:
        assert project.latest_sample_date == sample_date1
        expected = suggested_citation(Project.objects.get(pk=project.pk))
        assert suggested_citation(project, project.profiles_by_name) == expected
        assert str(sample_date1.year) in expected
