"""
Regression tests for Trello card 2256.

The multi-project report endpoint validated only that the requested project ids
exist, not that the caller belongs to them, and had no permission_classes. Any
authenticated user could request a GFCR report (private financial data) for any
project. GFCR has no public data policy, so a GFCR report is now members-only.
"""

from django.urls import reverse


def _gfcr_report(client, project, background=True):
    return client.post(
        reverse("reports"),
        {"report_type": "gfcr", "project_ids": [str(project.pk)], "background": background},
        format="json",
    )


def test_anonymous_cannot_request_report(db_setup, api_client_public, project1):
    assert _gfcr_report(api_client_public, project1).status_code == 401


def test_non_member_cannot_request_gfcr_report(db_setup, api_client3, project1):
    # profile3 is not a member of project1.
    assert _gfcr_report(api_client3, project1).status_code == 403


def test_member_passes_membership_gate(db_setup, api_client1, project1, project_profile1):
    # Membership gate passes for a member; must not be the 403 from the gate.
    assert _gfcr_report(api_client1, project1).status_code != 403
