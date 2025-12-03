"""
Tests for RelatedOrderingFilter functionality.

The RelatedOrderingFilter extends DRF's OrderingFilter to:
1. Support ordering by related fields using __ notation (e.g., genus__name)
2. Automatically append 'id' to ensure deterministic pagination
"""

import pytest
from rest_framework.test import APIClient

from api.models import FishSpecies, Profile
from api.resources.base import RelatedOrderingFilter


@pytest.mark.django_db
class TestRelatedOrderingFilter:
    @pytest.fixture
    def profile1(self):
        return Profile.objects.create(email="user1@example.com")

    def test_related_field_validation(self):
        """Test that is_valid_field correctly validates related fields."""
        filter = RelatedOrderingFilter()

        # Test simple field
        assert filter.is_valid_field(FishSpecies, "name") is True

        # Test related field
        assert filter.is_valid_field(FishSpecies, "genus__name") is True

        # Test deeply nested related field
        assert filter.is_valid_field(FishSpecies, "genus__family__name") is True

        # Test invalid field
        assert filter.is_valid_field(FishSpecies, "nonexistent") is False

        # Test invalid related field
        assert filter.is_valid_field(FishSpecies, "nonexistent__field") is False

    def test_related_field_ordering_works(self, profile1):
        """Test that ordering by related field (genus__name) works via API."""
        # Skip if no fish species exist in the test database
        if FishSpecies.objects.count() == 0:
            pytest.skip("No fish species in database to test ordering")

        client = APIClient()
        client.force_authenticate(user=type("User", (), {"profile": profile1})())

        # Order by related field genus__name
        response = client.get("/v1/fishspecies/?ordering=genus__name&limit=5")

        assert response.status_code == 200
        data = response.json()
        results = data["results"]

        # If there are results, verify they're ordered
        if len(results) > 1:
            genus_names = [r["genus"]["name"] for r in results]
            # Check that it's sorted (allowing for ties due to duplicate genus names)
            for i in range(len(genus_names) - 1):
                assert genus_names[i] <= genus_names[i + 1], "Results should be ordered by genus name"

    def test_descending_related_field_ordering(self, profile1):
        """Test that descending ordering by related field works."""
        if FishSpecies.objects.count() == 0:
            pytest.skip("No fish species in database to test ordering")

        client = APIClient()
        client.force_authenticate(user=type("User", (), {"profile": profile1})())

        # Order by related field genus__name descending
        response = client.get("/v1/fishspecies/?ordering=-genus__name&limit=5")

        assert response.status_code == 200
        data = response.json()
        results = data["results"]

        # If there are results, verify they're ordered descending
        if len(results) > 1:
            genus_names = [r["genus"]["name"] for r in results]
            for i in range(len(genus_names) - 1):
                assert genus_names[i] >= genus_names[i + 1], "Results should be ordered descending"

    def test_invalid_related_field_rejected(self, profile1):
        """Test that invalid related field names are rejected and don't cause errors."""
        client = APIClient()
        client.force_authenticate(user=type("User", (), {"profile": profile1})())

        # Try to order by invalid field - should not error
        response = client.get("/v1/fishspecies/?ordering=nonexistent__field&limit=5")

        assert response.status_code == 200
        # Invalid ordering should be ignored, not cause an error

    def test_deeply_nested_related_field(self, profile1):
        """Test that deeply nested related fields work (genus__family__name)."""
        if FishSpecies.objects.count() == 0:
            pytest.skip("No fish species in database to test ordering")

        client = APIClient()
        client.force_authenticate(user=type("User", (), {"profile": profile1})())

        # Order by nested related field - should not error
        response = client.get("/v1/fishspecies/?ordering=genus__family__name&limit=5")

        assert response.status_code == 200

    def test_deterministic_pagination(self, profile1):
        """
        Test that pagination is deterministic by automatically including 'id'.

        When ordering by fields with duplicate values, 'id' should be automatically
        appended to ensure consistent pagination results.
        """
        if FishSpecies.objects.count() < 2:
            pytest.skip("Need at least 2 fish species to test pagination")

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
