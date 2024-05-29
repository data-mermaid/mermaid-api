from datetime import date

import pytest
from django.urls import reverse

from api.models import (
    GFCRFinanceSolution,
    GFCRIndicatorSet,
    GFCRRevenue,
    ProjectProfile,
    RestrictedProjectSummarySampleEvent,
)


@pytest.fixture
def create_indicator_set_payload():
    return {
        "title": "Dustin's IS",
        "report_date": "2024-02-10",
        "report_year": 2024,
        "indicator_set_type": "annual_report",
        "f4_start_date": "1970-01-01",
        "f4_end_date": "2024-04-29",
        "finance_solutions": [
            {
                "name": "My FS",
                "sector": "green_shipping_and_cruise_ships",
                "revenues": [{"revenue_type": "debt_conversion"}],
                "investment_sources": [
                    {"investment_source": "public", "investment_type": "concessional_loan"},
                    {"investment_source": "philanthropy", "investment_type": "financial_guarantee"},
                ],
            }
        ],
    }


@pytest.fixture
def indicator_set(project1):
    return GFCRIndicatorSet.objects.create(
        project=project1,
        title="Dustin's IS",
        report_date="2024-02-10",
        indicator_set_type="annual_report",
        f4_start_date=date(1970, 1, 1),
        f4_end_date=date(2024, 4, 19),
    )


@pytest.fixture
def finance_solution(indicator_set):
    return GFCRFinanceSolution.objects.create(
        indicator_set=indicator_set,
        name="My FS",
        sector="green_shipping_and_cruise_ships",
    )


@pytest.fixture
def revenue(finance_solution):
    return GFCRRevenue.objects.create(
        finance_solution=finance_solution,
        revenue_type="debt_conversion",
    )


@pytest.fixture
def restricted_project_summary_sample_events(
    project1,
):
    return RestrictedProjectSummarySampleEvent.objects.create(
        project_id=project1.id,
        records=[
            {
                "sample_date": "2024-01-01",
                "protocols": {
                    "beltfish": {
                        "biomass_kgha_avg": 0,
                    },
                    "benthiclit": {
                        "percent_cover_benthic_category_avg": {"Hard coral": 5, "Macroalgae": 10},
                    },
                    "benthicpit": {
                        "percent_cover_benthic_category_avg": {"Hard coral": 10, "Macroalgae": 20},
                    },
                    "benthicpqt": {
                        "percent_cover_benthic_category_avg": {"Hard coral": 15, "Macroalgae": 30},
                    },
                },
            },
            {
                "sample_date": "2024-01-02",
                "protocols": {
                    "beltfish": {
                        "biomass_kgha_avg": 10,
                    },
                    "benthiclit": {
                        "percent_cover_benthic_category_avg": {"Hard coral": 20, "Macroalgae": 40}
                    },
                    "benthicpit": {
                        "percent_cover_benthic_category_avg": {"Hard coral": 25, "Macroalgae": 50}
                    },
                    "benthicpqt": {
                        "percent_cover_benthic_category_avg": {"Hard coral": 30, "Macroalgae": 60}
                    },
                },
            },
        ],
    )


def test_create_indicator_set_admin(
    db_setup,
    api_client1,
    project1,
    project_profile1,
    create_indicator_set_payload,
):
    project1.includes_gfcr = True
    project1.save()

    url = reverse("indicatorset-list", kwargs={"project_pk": project1.pk})
    request = api_client1.post(url, data=create_indicator_set_payload, format="json")

    assert request.status_code == 201
    response_data = request.json()

    indicator_set = GFCRIndicatorSet.objects.get(project=project1)
    finance_solution = indicator_set.finance_solutions.all()[0]
    investment_source = finance_solution.investment_sources.all()[0]
    revenue = finance_solution.revenues.all()[0]

    assert str(indicator_set.pk) == response_data["id"]

    finance_solution_data = response_data["finance_solutions"][0]

    assert finance_solution_data["id"] is not None
    assert str(finance_solution.pk) == finance_solution_data["id"]

    investment_source_data = finance_solution_data["investment_sources"][0]
    assert investment_source_data["id"] is not None
    assert str(investment_source.pk) == investment_source_data["id"]

    revenue_data = finance_solution_data["revenues"][0]
    assert revenue_data["id"] is not None
    assert str(revenue.pk) == revenue_data["id"]


def test_create_indicator_set_non_admin(
    db_setup,
    api_client1,
    project1,
    project_profile1,
    create_indicator_set_payload,
):
    project_profile1.role = ProjectProfile.COLLECTOR
    project_profile1.save()
    url = reverse("indicatorset-list", kwargs={"project_pk": project1.pk})
    request = api_client1.post(url, data=create_indicator_set_payload, format="json")

    assert request.status_code == 403


def test_update_indicator_set(
    db_setup,
    api_client1,
    project1,
    indicator_set,
):
    project1.includes_gfcr = True
    project1.save()

    # Create an indicator set
    url = reverse("indicatorset-detail", kwargs={"project_pk": project1.pk, "pk": indicator_set.id})
    create_request = api_client1.get(url, None, format="json")
    assert create_request.status_code == 200
    response_data = create_request.json()

    # Update the indicator set
    update_url = reverse(
        "indicatorset-detail", kwargs={"project_pk": project1.pk, "pk": indicator_set.id}
    )
    update_payload = response_data
    update_payload["title"] = "Updated Indicator Set"
    update_request = api_client1.put(update_url, data=update_payload, format="json")
    assert update_request.status_code == 200
    updated_response_data = update_request.json()

    # Verify the updated indicator set
    assert updated_response_data["title"] == "Updated Indicator Set"
    assert updated_response_data["id"] == str(indicator_set.id)


def test_coral_health_calculations(
    db_setup,
    api_client1,
    project1,
    indicator_set,
    restricted_project_summary_sample_events,
):
    project1.includes_gfcr = True
    project1.save()

    url = reverse("indicatorset-detail", kwargs={"project_pk": project1.pk, "pk": indicator_set.id})
    request = api_client1.get(url, None, format="json")

    assert request.status_code == 200
    response_data = request.json()

    assert response_data["f4_1_calc"] == 17.5
    assert response_data["f4_2_calc"] == 35
    assert response_data["f4_3_calc"] == 5


def test_reporting_range(
    db_setup,
    api_client1,
    project1,
    create_indicator_set_payload,
    belt_fish_project,
    update_summary_cache,
):
    project1.includes_gfcr = True
    project1.save()

    url = reverse("indicatorset-list", kwargs={"project_pk": project1.pk})
    request = api_client1.post(url, data=create_indicator_set_payload, format="json")
    assert request.status_code == 201
    response_data = request.json()
    assert response_data["f4_3"] is not None

    indicator_set = GFCRIndicatorSet.objects.get(pk=response_data["id"])
    indicator_set.f4_end_date = date(1980, 1, 1)
    indicator_set.save()

    url = reverse("indicatorset-detail", kwargs={"project_pk": project1.pk, "pk": indicator_set.id})
    request = api_client1.get(url, None, format="json")

    assert request.status_code == 200
    response_data = request.json()
    assert response_data["f4_3_calc"] is None
