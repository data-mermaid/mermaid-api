from api.models import InvertBeltTransect


def test_list_invert_attributes_returns_user_visible_hierarchy(
    db_setup, api_client1, all_test_invert_attributes
):
    """GET /v1/invertattributes/ returns ClassGOI, Order, Family, Genus, Species — not InvertClass."""
    response = api_client1.get("/v1/invertattributes/", format="json")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 5  # ClassGOI + Order + Family + Genus + Species

    ranks = {rec["taxonomic_rank"] for rec in data["results"]}
    assert "class" not in ranks
    assert ranks == {"class_goi", "order", "family", "genus", "species"}


def test_invert_attribute_species_fields(
    db_setup, api_client1, all_test_invert_attributes, invert_species_1
):
    """Species nodes include max_length, max_length_type, notes; others return None."""
    response = api_client1.get("/v1/invertattributes/", format="json")
    data = response.json()

    species_rec = next(r for r in data["results"] if r["taxonomic_rank"] == "species")
    assert float(species_rec["max_length"]) == float(invert_species_1.max_length)
    assert species_rec["max_length_type"] == invert_species_1.max_length_type
    assert species_rec["notes"] == invert_species_1.notes

    non_species = [r for r in data["results"] if r["taxonomic_rank"] != "species"]
    for rec in non_species:
        assert rec["max_length_type"] is None
        assert rec["max_length_source"] is None
        assert rec["notes"] is None


def test_invert_attribute_class_goi(
    db_setup,
    api_client1,
    all_test_invert_attributes,
    invert_class_goi_1,
):
    """class_goi is the InvertClassGroupOfInterest pk for every node in the hierarchy."""
    response = api_client1.get("/v1/invertattributes/", format="json")
    data = response.json()
    for rec in data["results"]:
        assert str(rec["class_goi"]) == str(
            invert_class_goi_1.pk
        ), f"{rec['taxonomic_rank']} node has wrong class_goi"


def test_invert_attribute_parent_chain(
    db_setup,
    api_client1,
    all_test_invert_attributes,
    invert_class_goi_1,
    invert_order_1,
    invert_family_1,
    invert_genus_1,
    invert_species_1,
):
    """parent field encodes the correct FK for each level; ClassGOI has no parent."""
    response = api_client1.get("/v1/invertattributes/", format="json")
    data = response.json()
    by_rank = {r["taxonomic_rank"]: r for r in data["results"]}

    assert by_rank["class_goi"]["parent"] is None
    assert str(by_rank["order"]["parent"]) == str(invert_class_goi_1.pk)
    assert str(by_rank["family"]["parent"]) == str(invert_order_1.pk)
    assert str(by_rank["genus"]["parent"]) == str(invert_family_1.pk)
    assert str(by_rank["species"]["parent"]) == str(invert_genus_1.pk)


def test_invert_attribute_detail(db_setup, api_client1, invert_species_1):
    """GET /v1/invertattributes/{id}/ returns the correct record."""
    response = api_client1.get(f"/v1/invertattributes/{invert_species_1.pk}/", format="json")
    assert response.status_code == 200
    data = response.json()
    assert data["taxonomic_rank"] == "species"
    assert float(data["max_length"]) == float(invert_species_1.max_length)


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


def test_sample_unit_method_search_fields_include_beltinvert():
    """SearchNonFieldFilter.SEARCH_FIELDS includes beltinvert observer name paths."""
    from api.resources.sampleunitmethods.sample_unit_methods import SearchNonFieldFilter

    fields = SearchNonFieldFilter.SEARCH_FIELDS
    assert "beltinvert__observers__profile__first_name" in fields
    assert "beltinvert__observers__profile__last_name" in fields
