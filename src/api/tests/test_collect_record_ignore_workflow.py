"""
The documented workflow for ignoring chosen warnings through the API
(docs/source/collectrecords.rst, "Ignoring warnings programmatically"):
validate, set chosen warnings to "ignore", PATCH the record's validations,
validate again, submit, and repeat while submitting creates new warnings.
These tests drive the same HTTP calls a script makes.
"""

import copy
from datetime import date, timedelta

from django.urls import reverse

from api.models import BeltFish, CollectRecord
from api.submission.validations import ERROR, IGNORE, OK, WARN


def _results(node):
    """Every validation result in a results tree, whatever its nesting."""
    if isinstance(node, dict):
        if "status" in node and "validation_id" in node:
            yield node
        else:
            for value in node.values():
                yield from _results(value)
    elif isinstance(node, list):
        for value in node:
            yield from _results(value)


def _ignore_warnings(validations, codes):
    n = 0
    for result in _results(validations["results"]):
        if result["status"] == WARN and result.get("code") in codes:
            result["status"] = IGNORE
            n += 1
    return n


def _codes(validations, status):
    return sorted(r["code"] for r in _results(validations["results"]) if r["status"] == status)


def _validate(client, project, record_ids):
    url = reverse("collectrecords-validate", args=[str(project.pk)])
    response = client.post(url, {"ids": [str(pk) for pk in record_ids]}, format="json")
    assert response.status_code == 200
    return response.json()


def _submit(client, project, record_id):
    url = reverse("collectrecords-submit", args=[str(project.pk)])
    response = client.post(url, {"ids": [str(record_id)]}, format="json")
    assert response.status_code == 200
    return response.json()[str(record_id)]


def _get(client, project, record_id):
    url = reverse("collectrecords-detail", args=[str(project.pk), str(record_id)])
    response = client.get(url, format="json")
    assert response.status_code == 200
    return response.json()


def _patch_validations(client, project, record_id, validations):
    url = reverse("collectrecords-detail", args=[str(project.pk), str(record_id)])
    response = client.patch(
        url, {"project": str(project.pk), "validations": validations}, format="json"
    )
    assert response.status_code == 200
    return response.json()


def _ignore_and_revalidate(client, project, record_id, codes):
    record = _get(client, project, record_id)
    _ignore_warnings(record["validations"], codes)
    _patch_validations(client, project, record_id, record["validations"])
    return _validate(client, project, [record_id])[str(record_id)]


def test_ignore_chosen_codes_then_submit(
    db_setup, api_client1, project1, invalid_collect_record_warn, belt_transect_width_condition2
):
    record_id = invalid_collect_record_warn.pk
    original_data = copy.deepcopy(invalid_collect_record_warn.data)

    out = _validate(api_client1, project1, [record_id])[str(record_id)]
    assert out["status"] == WARN
    # A field, an observation-level and two record-level warnings, among others.
    assert {"len_surveyed_out_of_range", "max_fish_size", "too_few_observations"} <= set(
        _codes(out["record"]["validations"], WARN)
    )

    # Ignoring some of the warnings leaves the record in warning, with the
    # ignores kept through revalidation and the record's data untouched.
    chosen = {"max_fish_size", "too_few_observations"}
    out = _ignore_and_revalidate(api_client1, project1, record_id, chosen)
    assert out["status"] == WARN
    assert _codes(out["record"]["validations"], IGNORE) == sorted(chosen)
    assert out["record"]["data"] == original_data
    assert _submit(api_client1, project1, record_id)["status"] == WARN

    # Ignoring the rest lets it validate ok and submit.
    remaining = set(_codes(out["record"]["validations"], WARN))
    out = _ignore_and_revalidate(api_client1, project1, record_id, remaining)
    assert out["status"] == OK
    assert out["record"]["stage"] == CollectRecord.VALIDATED_STAGE

    assert _submit(api_client1, project1, record_id)["status"] == OK
    assert not CollectRecord.objects.filter(pk=record_id).exists()
    assert BeltFish.objects.filter(collect_record_id=record_id).exists()


def test_ignored_error_does_not_stick(
    db_setup, api_client1, project1, invalid_collect_record_warn, belt_transect_width_condition2
):
    invalid_collect_record_warn.data["fishbelt_transect"]["len_surveyed"] = 1000
    invalid_collect_record_warn.save()
    record_id = invalid_collect_record_warn.pk

    out = _validate(api_client1, project1, [record_id])[str(record_id)]
    assert out["status"] == ERROR

    record = _get(api_client1, project1, record_id)
    for result in _results(record["validations"]["results"]):
        if result["status"] in (ERROR, WARN):
            result["status"] = IGNORE
    _patch_validations(api_client1, project1, record_id, record["validations"])

    out = _validate(api_client1, project1, [record_id])[str(record_id)]
    assert out["status"] == ERROR
    assert "len_surveyed_out_of_range" in _codes(out["record"]["validations"], ERROR)


def test_similar_date_warning_appears_after_sibling_submits(
    db_setup, api_client1, project1, valid_collect_record, belt_transect_width_condition2
):
    """
    Submitting one sample unit gives a sibling at the same site and management
    a few days apart a new similar-date warning, so a script has to repeat
    ignore/validate/submit until nothing changes.
    """
    first = valid_collect_record
    data = copy.deepcopy(first.data)
    year, month, day = (int(p) for p in data["sample_event"]["sample_date"].split("-"))
    later = date(year, month, day) + timedelta(days=3)
    data["sample_event"]["sample_date"] = f"{later:%Y-%m-%d}"
    data["fishbelt_transect"]["number"] = 2
    for obs in data["obs_belt_fishes"]:
        obs.pop("id", None)
    second = CollectRecord.objects.create(project=project1, profile=first.profile, data=data)

    out = _validate(api_client1, project1, [first.pk, second.pk])
    assert out[str(first.pk)]["status"] == OK
    assert out[str(second.pk)]["status"] == OK

    assert _submit(api_client1, project1, first.pk)["status"] == OK

    # Submit revalidates, and the sibling now warns.
    out = _submit(api_client1, project1, second.pk)
    assert out["status"] == WARN
    assert _codes(out["record"]["validations"], WARN) == ["similar_date_sample_unit"]

    # Second pass of the loop.
    out = _ignore_and_revalidate(api_client1, project1, second.pk, {"similar_date_sample_unit"})
    assert out["status"] == OK
    assert _submit(api_client1, project1, second.pk)["status"] == OK
