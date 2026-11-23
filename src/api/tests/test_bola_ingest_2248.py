"""
Regression test for Trello card 2248 (closed by the get_project_pk fix, card 2249).

The CSV ingest action authorized against a `project` multipart form field while it
wrote the parsed rows into the URL project. An admin of project A could ingest a
CSV into victim project B by sending `project=A` in the form and B in the URL. With
the URL authoritative, a mismatched body/form project is rejected.

The permission check runs before the CSV is parsed, so a mismatch is denied with
403 regardless of the file contents; a matching project reaches the ingest logic
(and fails later for an invalid CSV, not with 403).
"""

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse


def _dummy_csv():
    return SimpleUploadedFile("records.csv", b"not,a,valid,csv\n", content_type="text/csv")


def test_ingest_rejected_when_form_project_differs_from_url(
    db_setup, api_client1, project1, project_profile1, project2
):
    # api_client1 is ADMIN of project1, not a member of project2.
    url = reverse("collectrecords-ingest", args=[str(project2.pk)])
    response = api_client1.post(
        url,
        {"file": _dummy_csv(), "protocol": "fishbelt", "project": str(project1.pk)},
        format="multipart",
    )
    assert response.status_code == 403


def test_ingest_permission_passes_for_own_project(
    db_setup, api_client1, project1, project_profile1
):
    url = reverse("collectrecords-ingest", args=[str(project1.pk)])
    response = api_client1.post(
        url,
        {"file": _dummy_csv(), "protocol": "fishbelt", "project": str(project1.pk)},
        format="multipart",
    )
    # Permission passes for the admin's own project; the dummy CSV then fails
    # downstream, but never with a 403.
    assert response.status_code != 403
