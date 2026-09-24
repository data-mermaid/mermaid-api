from api.models import SUPERUSER_APPROVED, BenthicAttribute, FishSpecies, Revision
from api.models.base import PROPOSED


def test_attribute_queryset_hides_proposed_by_other_user(
    db_setup, api_client2, fish_genus1, profile1
):
    """Profile2 cannot see Profile1's proposed species or benthic attribute via GET."""
    FishSpecies.objects.create(
        name="Profile1 Proposed Species",
        genus=fish_genus1,
        biomass_constant_a=0.01,
        biomass_constant_b=3.0,
        biomass_constant_c=1.0,
        status=PROPOSED,
        created_by=profile1,
    )
    BenthicAttribute.objects.create(
        name="Profile1 Proposed Benthic",
        status=PROPOSED,
        created_by=profile1,
    )

    fish_response = api_client2.get("/v1/fishspecies/", format="json")
    assert fish_response.status_code == 200
    fish_names = {r["name"] for r in fish_response.json()["results"]}
    assert "Profile1 Proposed Species" not in fish_names

    benthic_response = api_client2.get("/v1/benthicattributes/", format="json")
    assert benthic_response.status_code == 200
    benthic_names = {r["name"] for r in benthic_response.json()["results"]}
    assert "Profile1 Proposed Benthic" not in benthic_names


def test_attribute_queryset_shows_own_proposed(db_setup, api_client1, fish_genus1, profile1):
    """Profile1 can see their own proposed attribute via sync pull (auth skipped on GET)."""
    species = FishSpecies.objects.create(
        name="My Own Proposed Species",
        genus=fish_genus1,
        biomass_constant_a=0.01,
        biomass_constant_b=3.0,
        biomass_constant_c=1.0,
        status=PROPOSED,
        created_by=profile1,
    )
    revision = Revision.objects.get(record_id=species.pk)
    last_revision = max(0, revision.revision_num - 1)

    data = {"fish_species": {"last_revision": last_revision}}
    response = api_client1.post("/v1/pull/", data, format="json")
    assert response.status_code == 200
    result = response.json()["fish_species"]

    update_ids = {r["id"] for r in result["updates"]}
    assert str(species.pk) in update_ids


def test_attribute_queryset_unauthenticated_shows_only_approved(
    db_setup, api_client_public, fish_genus1, profile1
):
    """Unauthenticated requests return only SUPERUSER_APPROVED attributes."""
    FishSpecies.objects.create(
        name="Proposed by profile1",
        genus=fish_genus1,
        biomass_constant_a=0.01,
        biomass_constant_b=3.0,
        biomass_constant_c=1.0,
        status=PROPOSED,
        created_by=profile1,
    )
    FishSpecies.objects.create(
        name="Approved Species",
        genus=fish_genus1,
        biomass_constant_a=0.02,
        biomass_constant_b=3.0,
        biomass_constant_c=1.0,
        status=SUPERUSER_APPROVED,
    )

    response = api_client_public.get("/v1/fishspecies/", format="json")
    assert response.status_code == 200
    names = {r["name"] for r in response.json()["results"]}
    assert "Approved Species" in names
    assert "Proposed by profile1" not in names


def test_pull_returns_visibility_removes_for_proposed_by_other(
    db_setup, api_client2, fish_genus1, profile1
):
    """Sync pull includes visibility removes for proposed-by-other attributes when revision was bumped."""
    species = FishSpecies.objects.create(
        name="Profile1 Proposed Pull Test",
        genus=fish_genus1,
        biomass_constant_a=0.01,
        biomass_constant_b=3.0,
        biomass_constant_c=1.0,
        status=PROPOSED,
        created_by=profile1,
    )
    revision = Revision.objects.get(record_id=species.pk)
    last_revision = max(0, revision.revision_num - 1)

    data = {"fish_species": {"last_revision": last_revision}}
    response = api_client2.post("/v1/pull/", data, format="json")
    assert response.status_code == 200
    result = response.json()["fish_species"]

    remove_ids = {r["id"] for r in result["removes"]}
    assert str(species.pk) in remove_ids
    update_ids = {r["id"] for r in result["updates"]}
    assert str(species.pk) not in update_ids


def test_attribute_demotion_triggers_visibility_remove(db_setup, api_client2, fish_genus1):
    """Demoting an approved attribute to proposed causes it to appear in removes for other users."""
    species = FishSpecies.objects.create(
        name="Demoted Species",
        genus=fish_genus1,
        biomass_constant_a=0.01,
        biomass_constant_b=3.0,
        biomass_constant_c=1.0,
        status=SUPERUSER_APPROVED,
    )
    revision_before_demotion = Revision.objects.get(record_id=species.pk).revision_num

    species.status = PROPOSED
    species.save()

    data = {"fish_species": {"last_revision": revision_before_demotion}}
    response = api_client2.post("/v1/pull/", data, format="json")
    assert response.status_code == 200
    result = response.json()["fish_species"]

    remove_ids = {r["id"] for r in result["removes"]}
    assert str(species.pk) in remove_ids
