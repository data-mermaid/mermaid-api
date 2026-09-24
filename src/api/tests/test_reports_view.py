from unittest.mock import patch

import pytest
from django.urls import reverse

from api.reports.summary_report import PROTOCOL_VIEW_MAPPING
from api.utils.reports import GFCR_REPORT_TYPE, SAMPLE_UNIT_METHOD_REPORT_TYPE


@pytest.mark.parametrize("protocol", list(PROTOCOL_VIEW_MAPPING.keys()))
def test_summary_report_all_protocols_accepted(api_client1, project1, protocol):
    """Every key in PROTOCOL_VIEW_MAPPING must be accepted by the ChoiceField.

    Regression test: DRF >= 3.16 flatten_choices_dict treats dict values as
    grouped choices, replacing valid keys with sub-keys like 'views' and
    'sheet_names'. Caught by checking each protocol returns 200, not 400.
    """
    url = reverse("reports")
    payload = {
        "report_type": SAMPLE_UNIT_METHOD_REPORT_TYPE,
        "project_ids": [str(project1.pk)],
        "protocol": protocol,
        "background": True,
    }
    with patch("api.resources.reports.create_sample_unit_method_summary_report_background"):
        response = api_client1.post(url, data=payload, format="json")

    assert response.status_code == 200, response.json()
    assert response.json() == {SAMPLE_UNIT_METHOD_REPORT_TYPE: "ok"}


def test_summary_report_invalid_protocol_rejected(api_client1, project1):
    url = reverse("reports")
    payload = {
        "report_type": SAMPLE_UNIT_METHOD_REPORT_TYPE,
        "project_ids": [str(project1.pk)],
        "protocol": "notaprotocol",
        "background": True,
    }
    response = api_client1.post(url, data=payload, format="json")

    assert response.status_code == 400
    assert "protocol" in response.json()


def test_gfcr_report_accepted(api_client1, project1):
    url = reverse("reports")
    payload = {
        "report_type": GFCR_REPORT_TYPE,
        "project_ids": [str(project1.pk)],
        "background": True,
    }
    with patch("api.resources.reports.gfcr.create_report_background"):
        response = api_client1.post(url, data=payload, format="json")

    assert response.status_code == 200
    assert response.json() == {GFCR_REPORT_TYPE: "ok"}


def test_unknown_report_type_rejected(api_client1, project1):
    url = reverse("reports")
    payload = {
        "report_type": "notareporttype",
        "project_ids": [str(project1.pk)],
        "background": True,
    }
    response = api_client1.post(url, data=payload, format="json")

    assert response.status_code == 400
    assert "Unknown report type" in response.json()


def test_empty_project_ids_rejected(api_client1):
    url = reverse("reports")
    payload = {
        "report_type": SAMPLE_UNIT_METHOD_REPORT_TYPE,
        "project_ids": [],
        "protocol": "fishbelt",
        "background": True,
    }
    response = api_client1.post(url, data=payload, format="json")

    assert response.status_code == 400
    assert "project_ids" in response.json()


def test_nonexistent_project_ids_rejected(api_client1):
    url = reverse("reports")
    payload = {
        "report_type": SAMPLE_UNIT_METHOD_REPORT_TYPE,
        "project_ids": ["00000000-0000-0000-0000-000000000000"],
        "protocol": "fishbelt",
        "background": True,
    }
    response = api_client1.post(url, data=payload, format="json")

    assert response.status_code == 400
    assert "project_ids" in response.json()
