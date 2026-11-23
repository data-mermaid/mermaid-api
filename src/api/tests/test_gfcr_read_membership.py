"""
Regression tests for Trello card 2233 (read side).

GFCR has no public data policy, so reading a project's GFCR indicator sets must
require project membership. The viewset used AuthenticatedReadOnlyPermission,
which let any logged-in user read any project's GFCR financial data (BOLA).
"""

from datetime import date

import pytest
from django.urls import reverse

from api.models import GFCRIndicatorSet, ProjectProfile


@pytest.fixture
def gfcr_indicator_set(project1):
    project1.includes_gfcr = True
    project1.save()
    return GFCRIndicatorSet.objects.create(
        project=project1,
        title="Baseline",
        report_date="2024-02-10",
        indicator_set_type="report",
        f4_start_date=date(1970, 1, 1),
        f4_end_date=date(2024, 4, 19),
    )


def test_member_can_read_indicator_sets(
    db_setup, api_client1, project1, project_profile1, gfcr_indicator_set
):
    url = reverse("indicatorset-list", kwargs={"project_pk": project1.pk})
    response = api_client1.get(url, format="json")
    assert response.status_code == 200


def test_non_member_cannot_read_indicator_sets(db_setup, api_client3, project1, gfcr_indicator_set):
    # api_client3 (profile3) is not a member of project1.
    url = reverse("indicatorset-list", kwargs={"project_pk": project1.pk})
    response = api_client3.get(url, format="json")
    assert response.status_code in (403, 404)


def test_readonly_member_can_read_indicator_sets(
    db_setup, api_client3, project1, profile3, gfcr_indicator_set
):
    # A READONLY member is allowed to read.
    ProjectProfile.objects.create(project=project1, profile=profile3, role=ProjectProfile.READONLY)
    url = reverse("indicatorset-list", kwargs={"project_pk": project1.pk})
    response = api_client3.get(url, format="json")
    assert response.status_code == 200
