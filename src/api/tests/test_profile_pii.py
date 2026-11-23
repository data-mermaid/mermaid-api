"""
Regression tests for Trello card 2250.

The /v1/profiles/ endpoint requires authentication (an anonymous request gets
401), so the real exposure is that ANY authenticated user could harvest every
user's email and name through the `fields` query parameter. `fields` rebuilt the
serializer and validated requested names against the whole model, so it reached
columns the serializer deliberately omits (email, first_name, last_name).

The fix restricts `fields` to what the base serializer already exposes. These
tests pin that: a PII column cannot be selected, a serializer field still can.
"""

from django.urls import reverse


def _rows(response):
    data = response.data
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return data


def test_fields_param_cannot_select_email(db_setup, api_client3, profile1):
    response = api_client3.get(reverse("profile-list"), {"fields": "id,email"}, format="json")
    assert response.status_code == 400


def test_fields_param_cannot_select_name(db_setup, api_client3, profile1):
    response = api_client3.get(
        reverse("profile-list"), {"fields": "id,first_name,last_name"}, format="json"
    )
    assert response.status_code == 400


def test_fields_param_allows_serializer_field(db_setup, api_client3, profile1):
    response = api_client3.get(reverse("profile-list"), {"fields": "id"}, format="json")
    assert response.status_code == 200
    rows = _rows(response)
    assert rows
    for row in rows:
        assert "id" in row
        assert "email" not in row
        assert "first_name" not in row
