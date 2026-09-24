from decimal import Decimal

from api.models import InvertBeltTransect, InvertSpecies
from api.models.base import PROPOSED


def test_list_invert_attributes_returns_user_visible_hierarchy(
    db_setup, api_client1, all_test_invert_attributes
):
    """GET /v1/invertattributes/ returns GoI, Class, Order, Family, Genus, Species."""
    response = api_client1.get("/v1/invertattributes/", format="json")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 6  # GoI + Class + Order + Family + Genus + Species

    ranks = {rec["taxonomic_rank"] for rec in data["results"]}
    assert "class_goi" not in ranks
    assert ranks == {"goi", "class", "order", "family", "genus", "species"}


def test_invert_attribute_species_fields(
    db_setup, api_client1, all_test_invert_attributes, invert_species_1
):
    """Species nodes include max_length, max_length_type, notes; others return None."""
    response = api_client1.get("/v1/invertattributes/", format="json")
    data = response.json()

    species_rec = next(r for r in data["results"] if r["taxonomic_rank"] == "species")
    assert Decimal(str(species_rec["max_length"])) == Decimal(str(invert_species_1.max_length))
    assert species_rec["max_length_type"] == invert_species_1.max_length_type
    assert species_rec["notes"] == invert_species_1.notes

    non_species = [r for r in data["results"] if r["taxonomic_rank"] != "species"]
    for rec in non_species:
        assert rec["max_length_type"] is None
        assert rec["max_length_source"] is None
        assert rec["notes"] is None


def test_invert_attribute_group_of_interest(
    db_setup, api_client1, all_test_invert_attributes, invert_group_of_interest_1
):
    """genus and species return group_of_interest; class/order/family return None; goi returns itself."""
    response = api_client1.get("/v1/invertattributes/", format="json")
    data = response.json()
    by_rank = {r["taxonomic_rank"]: r for r in data["results"]}

    assert str(by_rank["genus"]["group_of_interest"]) == str(invert_group_of_interest_1.pk)
    assert str(by_rank["species"]["group_of_interest"]) == str(invert_group_of_interest_1.pk)
    assert str(by_rank["goi"]["group_of_interest"]) == str(invert_group_of_interest_1.pk)
    for rank in ("class", "order", "family"):
        assert by_rank[rank]["group_of_interest"] is None


def test_invert_attribute_parent_chain(
    db_setup,
    api_client1,
    all_test_invert_attributes,
    invert_class_1,
    invert_order_1,
    invert_family_1,
    invert_genus_1,
    invert_species_1,
):
    """parent field encodes the correct FK for each level; GoI and Class have no parent."""
    response = api_client1.get("/v1/invertattributes/", format="json")
    data = response.json()
    by_rank = {r["taxonomic_rank"]: r for r in data["results"]}

    assert by_rank["goi"]["parent"] is None
    assert by_rank["class"]["parent"] is None
    assert str(by_rank["order"]["parent"]) == str(invert_class_1.pk)
    assert str(by_rank["family"]["parent"]) == str(invert_order_1.pk)
    assert str(by_rank["genus"]["parent"]) == str(invert_family_1.pk)
    assert str(by_rank["species"]["parent"]) == str(invert_genus_1.pk)


def test_invert_attribute_detail(db_setup, api_client1, invert_species_1):
    """GET /v1/invertattributes/{id}/ returns the correct record."""
    response = api_client1.get(f"/v1/invertattributes/{invert_species_1.pk}/", format="json")
    assert response.status_code == 200
    data = response.json()
    assert data["taxonomic_rank"] == "species"
    assert Decimal(str(data["max_length"])) == Decimal(str(invert_species_1.max_length))


def test_invert_goi_attribute_detail(db_setup, api_client1, invert_group_of_interest_1):
    """GET /v1/invertattributes/{id}/ works for a GoI node."""
    response = api_client1.get(
        f"/v1/invertattributes/{invert_group_of_interest_1.pk}/", format="json"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["taxonomic_rank"] == "goi"
    assert data["name"] == invert_group_of_interest_1.name
    assert str(data["group_of_interest"]) == str(invert_group_of_interest_1.pk)


def test_invert_belt_transect_list(db_setup, api_client1, project1, invert_belt_transect1):
    """GET /v1/projects/{id}/invertbelttransects/ lists transects for the project."""
    response = api_client1.get(f"/v1/projects/{project1.pk}/invertbelttransects/", format="json")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert str(data["results"][0]["id"]) == str(invert_belt_transect1.pk)


def test_invert_belt_transect_create(
    db_setup, api_client1, project1, sample_event1, invert_belt_transect_width_1m, invert_size_bin_1
):
    """POST creates a new InvertBeltTransect."""
    payload = {
        "sample_event": str(sample_event1.pk),
        "width": str(invert_belt_transect_width_1m.pk),
        "size_bin": str(invert_size_bin_1.pk),
        "depth": 10,
        "len_surveyed": 25,
        "number": 2,
        "label": "",
    }
    response = api_client1.post(
        f"/v1/projects/{project1.pk}/invertbelttransects/",
        data=payload,
        format="json",
    )
    assert response.status_code == 201
    assert InvertBeltTransect.objects.filter(number=2).exists()


def test_invert_belt_transect_retrieve(
    db_setup, api_client1, project1, invert_belt_transect1, invert_belt_transect_width_1m
):
    """GET /v1/projects/{id}/invertbelttransects/{id}/ returns the correct record with all fields."""
    response = api_client1.get(
        f"/v1/projects/{project1.pk}/invertbelttransects/{invert_belt_transect1.pk}/",
        format="json",
    )
    assert response.status_code == 200
    data = response.json()
    assert str(data["id"]) == str(invert_belt_transect1.pk)
    assert str(data["width"]) == str(invert_belt_transect_width_1m.pk)
    assert data["number"] == 1


def test_invert_belt_transect_delete(db_setup, api_client1, project1, invert_belt_transect1):
    """DELETE removes the InvertBeltTransect."""
    pk = invert_belt_transect1.pk
    response = api_client1.delete(
        f"/v1/projects/{project1.pk}/invertbelttransects/{pk}/",
        format="json",
    )
    assert response.status_code == 204
    assert not InvertBeltTransect.objects.filter(pk=pk).exists()


def test_invertbelttransect_not_accessible_cross_project(
    db_setup, api_client3, project1, invert_belt_transect1
):
    """User with no membership in project1 cannot read project1's invertbelttransects."""
    response = api_client3.get(f"/v1/projects/{project1.pk}/invertbelttransects/", format="json")
    assert response.status_code == 403


def test_invertbelttransect_filter_len_surveyed(
    db_setup, api_client1, project1, invert_belt_transect1
):
    """len_surveyed RangeFilter includes and excludes the transect correctly."""
    url = f"/v1/projects/{project1.pk}/invertbelttransects/"
    resp = api_client1.get(url, {"len_surveyed_min": 50}, format="json")
    assert resp.status_code == 200
    assert resp.json()["count"] == 1

    resp = api_client1.get(url, {"len_surveyed_min": 100}, format="json")
    assert resp.status_code == 200
    assert resp.json()["count"] == 0


def test_invertbelttransect_filter_depth(db_setup, api_client1, project1, invert_belt_transect1):
    """depth RangeFilter includes and excludes the transect correctly."""
    url = f"/v1/projects/{project1.pk}/invertbelttransects/"
    resp = api_client1.get(url, {"depth_max": 5}, format="json")
    assert resp.status_code == 200
    assert resp.json()["count"] == 1

    resp = api_client1.get(url, {"depth_max": 1}, format="json")
    assert resp.status_code == 200
    assert resp.json()["count"] == 0


def test_invertbelttransect_filter_width(
    db_setup,
    api_client1,
    project1,
    invert_belt_transect1,
    invert_belt_transect_width_1m,
    invert_belt_transect_width_2m,
):
    """width filter matches the assigned width and excludes a different one."""
    url = f"/v1/projects/{project1.pk}/invertbelttransects/"
    resp = api_client1.get(url, {"width": str(invert_belt_transect_width_1m.pk)}, format="json")
    assert resp.status_code == 200
    assert resp.json()["count"] == 1

    resp = api_client1.get(url, {"width": str(invert_belt_transect_width_2m.pk)}, format="json")
    assert resp.status_code == 200
    assert resp.json()["count"] == 0


def test_invertbelttransect_filter_size_bin(
    db_setup, api_client1, project1, invert_belt_transect1, invert_size_bin_1, invert_size_bin_2
):
    """size_bin filter matches the assigned bin and excludes a different one."""
    url = f"/v1/projects/{project1.pk}/invertbelttransects/"
    resp = api_client1.get(url, {"size_bin": str(invert_size_bin_1.pk)}, format="json")
    assert resp.status_code == 200
    assert resp.json()["count"] == 1

    resp = api_client1.get(url, {"size_bin": str(invert_size_bin_2.pk)}, format="json")
    assert resp.status_code == 200
    assert resp.json()["count"] == 0


def test_post_invert_species_creates_proposed(db_setup, api_client1, invert_genus_1):
    """POST /v1/invertspecies/ creates a proposed InvertSpecies owned by the authenticated user."""
    payload = {"name": "newspecies", "genus": str(invert_genus_1.pk)}
    response = api_client1.post("/v1/invertspecies/", data=payload, format="json")
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == PROPOSED
    assert data["display_name"] == f"{invert_genus_1.name} newspecies"
    assert InvertSpecies.objects.filter(name="newspecies", genus=invert_genus_1).exists()


def test_sample_unit_method_search_fields_include_beltinvert():
    """SearchNonFieldFilter.SEARCH_FIELDS includes beltinvert observer name paths."""
    from api.resources.sampleunitmethods.sample_unit_methods import SearchNonFieldFilter

    fields = SearchNonFieldFilter.SEARCH_FIELDS
    assert "beltinvert__observers__profile__first_name" in fields
    assert "beltinvert__observers__profile__last_name" in fields
