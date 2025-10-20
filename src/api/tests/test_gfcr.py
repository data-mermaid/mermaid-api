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
        "indicator_set_type": "report",
        "f4_start_date": "1970-01-01",
        "f4_end_date": "2024-04-29",
        "finance_solutions": [
            {
                "name": "My FS",
                "sector": "ce_waste_management",
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
        indicator_set_type="report",
        f4_start_date=date(1970, 1, 1),
        f4_end_date=date(2024, 4, 19),
    )


@pytest.fixture
def finance_solution(indicator_set):
    return GFCRFinanceSolution.objects.create(
        indicator_set=indicator_set,
        name="My FS",
        sector="ce_waste_management",
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
    print(create_indicator_set_payload)

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


def test_notes_in_report_export(
    db_setup,
    project1,
):
    """Test that all notes fields are included in the GFCR report export."""
    from openpyxl import load_workbook

    from api.reports.gfcr import create_report

    project1.includes_gfcr = True
    project1.save()

    # Create indicator set with all notes fields populated
    indicator_set = GFCRIndicatorSet.objects.create(
        project=project1,
        title="Test Indicator Set",
        report_date="2024-02-10",
        indicator_set_type="report",
        f1_notes="F1 test notes",
        f2_notes="F2 test notes",
        f3_notes="F3 test notes",
        f4_notes="F4 test notes",
        f4_start_date=date(1970, 1, 1),
        f4_end_date=date(2024, 4, 19),
        f5_notes="F5 test notes",
        f6_notes="F6 test notes",
        f7_notes="F7 test notes",
    )

    # Create finance solution with notes
    finance_solution = GFCRFinanceSolution.objects.create(
        indicator_set=indicator_set,
        name="Test Finance Solution",
        sector="ce_waste_management",
        notes="Finance solution notes",
    )

    # Create investment with notes
    from api.models import GFCRInvestmentSource

    GFCRInvestmentSource.objects.create(
        finance_solution=finance_solution,
        investment_source="public",
        investment_type="grant",
        investment_amount=10000,
        notes="Investment notes",
    )

    # Create revenue with notes
    GFCRRevenue.objects.create(
        finance_solution=finance_solution,
        revenue_type="ecotourism",
        revenue_amount=5000,
        notes="Revenue notes",
    )

    # Generate report
    report_path = create_report([project1.id])
    assert report_path is not None

    # Load the workbook and verify notes are present
    wb = load_workbook(report_path)

    # Check F1 sheet - should have notes in column 8
    f1_sheet = wb["F1"]
    f1_row = list(f1_sheet.iter_rows(min_row=2, max_row=2, values_only=True))[0]
    assert f1_row[7] == "F1 test notes", f"F1 notes not found. Row: {f1_row}"

    # Check F2 sheet - should have notes in column 7
    f2_sheet = wb["F2"]
    f2_rows = list(f2_sheet.iter_rows(min_row=2, values_only=True))
    # All F2 rows should have the same notes
    for row in f2_rows:
        if row[0] is not None:  # Skip empty rows
            assert row[6] == "F2 test notes", f"F2 notes not found in row: {row}"
            break

    # Check F3 sheet - should have notes in column 7
    f3_sheet = wb["F3"]
    f3_rows = list(f3_sheet.iter_rows(min_row=2, values_only=True))
    for row in f3_rows:
        if row[0] is not None:
            assert row[6] == "F3 test notes", f"F3 notes not found in row: {row}"
            break

    # Check F4 sheet - should have notes in column 9
    f4_sheet = wb["F4"]
    f4_rows = list(f4_sheet.iter_rows(min_row=2, values_only=True))
    for row in f4_rows:
        if row[0] is not None:
            assert row[8] == "F4 test notes", f"F4 notes not found in row: {row}"
            break

    # Check F5 sheet - should have notes in column 7
    f5_sheet = wb["F5"]
    f5_rows = list(f5_sheet.iter_rows(min_row=2, values_only=True))
    for row in f5_rows:
        if row[0] is not None:
            assert row[6] == "F5 test notes", f"F5 notes not found in row: {row}"
            break

    # Check F6 sheet - should have notes in column 7
    f6_sheet = wb["F6"]
    f6_rows = list(f6_sheet.iter_rows(min_row=2, values_only=True))
    for row in f6_rows:
        if row[0] is not None:
            assert row[6] == "F6 test notes", f"F6 notes not found in row: {row}"
            break

    # Check F7 sheet - should have notes in column 7
    f7_sheet = wb["F7"]
    f7_rows = list(f7_sheet.iter_rows(min_row=2, values_only=True))
    for row in f7_rows:
        if row[0] is not None:
            assert row[6] == "F7 test notes", f"F7 notes not found in row: {row}"
            break

    # Check BusinessesFinanceSolutions sheet - should have notes in column 12
    bfs_sheet = wb["BusinessesFinanceSolutions"]
    bfs_row = list(bfs_sheet.iter_rows(min_row=2, max_row=2, values_only=True))[0]
    assert (
        bfs_row[11] == "Finance solution notes"
    ), f"Finance solution notes not found. Row: {bfs_row}"

    # Check Investments sheet - should have notes in column 11
    inv_sheet = wb["Investments"]
    inv_row = list(inv_sheet.iter_rows(min_row=2, max_row=2, values_only=True))[0]
    assert inv_row[10] == "Investment notes", f"Investment notes not found. Row: {inv_row}"

    # Check Revenues sheet - should have notes in column 11
    rev_sheet = wb["Revenues"]
    rev_row = list(rev_sheet.iter_rows(min_row=2, max_row=2, values_only=True))[0]
    assert rev_row[10] == "Revenue notes", f"Revenue notes not found. Row: {rev_row}"

    # Clean up
    import os

    os.remove(report_path)
