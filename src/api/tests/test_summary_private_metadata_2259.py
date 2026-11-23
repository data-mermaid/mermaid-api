"""
Regression tests for Trello card 2259.

The global summary-sample-event view nulled private metric values but still returned the
row (site name, GPS, management, admins, tags, sample date) for every non-TEST project,
including fully-PRIVATE ones, to anonymous callers. A row whose every protocol policy is
"private" is now hidden unless the caller is a member of its project.
"""

import uuid

from django.contrib.gis.geos import Point
from django.urls import reverse

from api.models import Project, ProjectProfile, SummarySampleEventModel
from api.utils.project import DATA_POLICY_FIELDS

COMMON = dict(
    site_name="S",
    location=Point(0.0, 0.0, srid=4326),
    contact_link="x",
    country_id=uuid.uuid4(),
    country_name="C",
    reef_type="r",
    reef_zone="z",
    reef_exposure="e",
    management_id=uuid.uuid4(),
    management_name="M",
)


def _row(project, policy):
    fields = dict(COMMON)
    fields.update({f: policy for f in DATA_POLICY_FIELDS})
    return SummarySampleEventModel.objects.create(
        sample_event_id=uuid.uuid4(),
        site_id=uuid.uuid4(),
        project_id=project.pk,
        project_name=project.name,
        project_status=Project.OPEN,
        **fields,
    )


def _project_ids(response):
    data = response.json()
    rows = data["results"] if isinstance(data, dict) and "results" in data else data
    return {row["project_id"] for row in rows}


def test_anonymous_excluded_from_fully_private_rows(db_setup, api_client_public):
    public = Project.objects.create(name="pub-2259")
    private = Project.objects.create(name="priv-2259")
    _row(public, "public summary")
    _row(private, "private")

    ids = _project_ids(api_client_public.get(reverse("summarysampleevent-list"), format="json"))
    assert str(public.pk) in ids
    assert str(private.pk) not in ids


def test_member_sees_own_fully_private_rows(db_setup, api_client3, profile3):
    private = Project.objects.create(name="priv-2259b")
    ProjectProfile.objects.create(project=private, profile=profile3, role=ProjectProfile.READONLY)
    _row(private, "private")

    ids = _project_ids(api_client3.get(reverse("summarysampleevent-list"), format="json"))
    assert str(private.pk) in ids
