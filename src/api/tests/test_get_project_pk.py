"""
Unit tests for permissions.get_project_pk (no DB needed).

Pins the rule that the URL identifies the project for the permission decision and
the request body can never override it (BOLA root cause, Trello card 2249).
"""

from types import SimpleNamespace

import pytest
from rest_framework.exceptions import PermissionDenied

from api.permissions import get_project_pk

PROJECT_A = "11111111-1111-1111-1111-111111111111"
PROJECT_B = "22222222-2222-2222-2222-222222222222"


def _req(data):
    return SimpleNamespace(data=data)


def _view(kwargs):
    return SimpleNamespace(kwargs=kwargs)


def test_nested_project_pk_matching_body_resolves_to_url():
    pk = get_project_pk(_req({"project": PROJECT_B}), _view({"project_pk": PROJECT_B}))
    assert pk == PROJECT_B


def test_nested_project_pk_mismatched_body_is_rejected():
    # URL targets B, body claims A -> BOLA attempt, must be denied.
    with pytest.raises(PermissionDenied):
        get_project_pk(_req({"project": PROJECT_A}), _view({"project_pk": PROJECT_B}))


def test_project_endpoint_pk_mismatched_body_is_rejected():
    with pytest.raises(PermissionDenied):
        get_project_pk(_req({"project": PROJECT_A}), _view({"pk": PROJECT_B}))


def test_body_used_only_when_url_has_no_project():
    pk = get_project_pk(_req({"project": PROJECT_A}), _view({}))
    assert pk == PROJECT_A


def test_nested_project_pk_without_body():
    pk = get_project_pk(_req({}), _view({"project_pk": PROJECT_B}))
    assert pk == PROJECT_B


def test_none_when_nothing_identifies_a_project():
    assert get_project_pk(_req({}), _view({})) is None


def test_list_body_matching_url_resolves():
    pk = get_project_pk(_req([{"project": PROJECT_B}]), _view({"project_pk": PROJECT_B}))
    assert pk == PROJECT_B


def test_list_body_with_mismatched_element_is_rejected():
    with pytest.raises(PermissionDenied):
        get_project_pk(
            _req([{"project": PROJECT_B}, {"project": PROJECT_A}]),
            _view({"project_pk": PROJECT_B}),
        )
