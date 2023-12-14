from api.utils.sample_units import delete_orphaned_sample_unit


def test_delete_orphaned_sample_unit_clean_orphaned(
    benthic_lit_project, benthic_transect1, benthic_lit1
):
    assert delete_orphaned_sample_unit(benthic_transect1, deleted_tm=benthic_lit1) is True


def test_delete_orphaned_sample_unit_not_cleaned_orphaned(
    benthic_lit_project,
    benthic_pit_project,
    benthic_transect1,
    benthic_lit1,
    benthic_pit1,
):
    assert delete_orphaned_sample_unit(benthic_transect1, deleted_tm=benthic_lit1) is False
