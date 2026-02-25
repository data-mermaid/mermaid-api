"""
Tests for RelatedOrderingFilter functionality.

The RelatedOrderingFilter extends DRF's OrderingFilter to:
1. Support ordering by related fields using __ notation (e.g., genus__name)
2. Automatically append 'id' to ensure deterministic pagination
"""

from rest_framework.test import APIClient

from api.models import FishSpecies
from api.resources.base import RelatedOrderingFilter


def test_related_field_validation():
    """Test that is_valid_field correctly validates related fields."""
    filter = RelatedOrderingFilter()

    assert filter.is_valid_field(FishSpecies, "name") is True
    assert filter.is_valid_field(FishSpecies, "genus__name") is True
    assert filter.is_valid_field(FishSpecies, "genus__family__name") is True
    assert filter.is_valid_field(FishSpecies, "nonexistent") is False
    assert filter.is_valid_field(FishSpecies, "nonexistent__field") is False


def test_related_field_ordering_works(profile1, all_test_fish_attributes):
    genera_lookup = {str(f.genus.pk): f.genus.name for f in FishSpecies.objects.all()}
    client = APIClient()
    client.force_authenticate(user=type("User", (), {"profile": profile1})())

    response = client.get("/v1/fishspecies/?ordering=genus__name&limit=5")

    assert response.status_code == 200
    data = response.json()
    results = data["results"]

    assert len(results) > 1
    genus_names = [genera_lookup.get(r["genus"]) for r in results]
    # Check that it's sorted (allowing for ties due to duplicate genus names)
    for i in range(len(genus_names) - 1):
        assert genus_names[i] <= genus_names[i + 1], "Results should be ordered by genus name"


def test_descending_related_field_ordering(profile1, all_test_fish_attributes):
    genera_lookup = {str(f.genus.pk): f.genus.name for f in FishSpecies.objects.all()}
    client = APIClient()
    client.force_authenticate(user=type("User", (), {"profile": profile1})())

    response = client.get("/v1/fishspecies/?ordering=-genus__name&limit=5")

    assert response.status_code == 200
    data = response.json()
    results = data["results"]

    assert len(results) > 1
    genus_names = [genera_lookup.get(r["genus"]) for r in results]
    for i in range(len(genus_names) - 1):
        assert genus_names[i] >= genus_names[i + 1], "Results should be ordered descending"


def test_invalid_related_field_rejected(profile1):
    client = APIClient()
    client.force_authenticate(user=type("User", (), {"profile": profile1})())

    # Try to order by invalid field - should not error
    response = client.get("/v1/fishspecies/?ordering=nonexistent__field&limit=5")

    assert response.status_code == 200


def test_deeply_nested_related_field(profile1, all_test_fish_attributes):
    client = APIClient()
    client.force_authenticate(user=type("User", (), {"profile": profile1})())

    # Order by nested related field - should not error
    response = client.get("/v1/fishspecies/?ordering=genus__family__name&limit=5")

    assert response.status_code == 200


def test_deterministic_pagination(profile1, all_test_fish_attributes):
    """
    Test that pagination is deterministic by automatically including 'id'.

    When ordering by fields with duplicate values, 'id' should be automatically
    appended to ensure consistent pagination results.
    """
    client = APIClient()
    client.force_authenticate(user=type("User", (), {"profile": profile1})())

    # Make multiple requests with the same ordering
    response1 = client.get("/v1/fishspecies/?ordering=genus__name&limit=10")
    response2 = client.get("/v1/fishspecies/?ordering=genus__name&limit=10")

    assert response1.status_code == 200
    assert response2.status_code == 200

    # Results should be identical (deterministic)
    ids1 = [r["id"] for r in response1.json()["results"]]
    ids2 = [r["id"] for r in response2.json()["results"]]

    assert ids1 == ids2, "Pagination should be deterministic across multiple requests"
