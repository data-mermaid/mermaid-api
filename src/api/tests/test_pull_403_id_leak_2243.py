"""
Regression test for Trello card 2243.

On a 401/403 source, pull still queried the project and returned its record UUIDs in
error.record_ids, so an authenticated non-member could enumerate any project's record
ids. The denial branch now returns only the error code - no record_ids.
"""

from django.urls import reverse  # noqa: F401 (kept for symmetry; route is unnamed)


def test_pull_denied_source_does_not_leak_record_ids(db_setup, api_client3, project1, site1):
    # profile3 (api_client3) is not a member of project1.
    payload = {"project_sites": {"project": str(project1.pk), "last_revision": 0}}
    response = api_client3.post("/v1/pull/", payload, format="json")
    assert response.status_code == 200
    source = response.json()["project_sites"]
    assert source["error"]["code"] in (401, 403)
    assert "record_ids" not in source["error"]
    assert source["updates"] == []
    assert source["deletes"] == []
