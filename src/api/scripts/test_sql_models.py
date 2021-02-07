from api.models import (
    BeltFishObsSQLModel,
    BeltFishObsView,
    BeltFishSESQLModel,
    BeltFishSEView,
    BeltFishSUSQLModel,
    BeltFishSUView,
    BenthicLITObsSQLModel,
    BenthicLITSESQLModel,
    BenthicLITSUSQLModel,
    BenthicPITObsSQLModel,
    BenthicPITObsView,
    BenthicPITSESQLModel,
    BenthicPITSEView,
    BenthicPITSUSQLModel,
    BenthicPITSUView,
    BenthicLITObsView,
    BenthicLITSUView,
    BenthicLITSEView,
    BleachingQCColoniesBleachedObsSQLModel,
    BleachingQCQuadratBenthicPercentObsSQLModel,
    BleachingQCSESQLModel,
    BleachingQCSUSQLModel,
    BleachingQCColoniesBleachedObsView,
    BleachingQCQuadratBenthicPercentObsView,
    BleachingQCSEView,
    BleachingQCSUView,
    HabitatComplexityObsSQLModel,
    HabitatComplexitySESQLModel,
    HabitatComplexitySUSQLModel,
    HabitatComplexityObsView,
    HabitatComplexitySEView,
    HabitatComplexitySUView,
)

fish_belt_project_id = "4080679f-1145-4d13-8afb-c2f694004f97"
benthic_pit_project_id = "4080679f-1145-4d13-8afb-c2f694004f97"
benthic_lit_project_id = "2d6cee25-c0ff-4f6f-a8cd-667d3f2b914b"
hb_project_id = "0c000a00-ffae-44a1-9412-4f18afa7635f"
bleaching_project_id = "d065cba4-ed09-47fd-89fb-2293fbbf617f"


def _compare_records(vw_result, sql_result):
    sql_count = sql_result.count()
    vw_count = vw_result.count()
    assert sql_count == vw_count

    sql_record = sql_result[0]
    vw_record = vw_result[0]

    fields = vw_record._meta.get_fields()
    for field in fields:
        sql_field_value = getattr(sql_record, field.name, None)
        vw_field_value = getattr(vw_record, field.name, None)

        assert sql_field_value == vw_field_value

    return sql_count, vw_count


def test_belt_fish_obs_sql_model():
    sql_result = (
        BeltFishObsSQLModel.objects.all()
        .sql_table(project_id=fish_belt_project_id)
        .order_by("id")
    )
    vw_result = BeltFishObsView.objects.filter(
        project_id=fish_belt_project_id
    ).order_by("id")

    return _compare_records(vw_result, sql_result)


def test_belt_fish_su_sql_model():
    sql_result = (
        BeltFishSUSQLModel.objects.all()
        .sql_table(project_id=fish_belt_project_id)
        .order_by("id")
    )
    vw_result = BeltFishSUView.objects.filter(project_id=fish_belt_project_id).order_by(
        "id"
    )

    return _compare_records(vw_result, sql_result)


def test_belt_fish_se_sql_model():
    sql_result = (
        BeltFishSESQLModel.objects.all()
        .sql_table(project_id=fish_belt_project_id)
        .order_by("id")
    )
    vw_result = BeltFishSEView.objects.filter(project_id=fish_belt_project_id).order_by(
        "id"
    )

    return _compare_records(vw_result, sql_result)


def test_benthic_pit_obs_sql_model():
    sql_result = (
        BenthicPITObsSQLModel.objects.all()
        .sql_table(project_id=benthic_pit_project_id)
        .order_by("id")
    )
    vw_result = BenthicPITObsView.objects.filter(
        project_id=benthic_pit_project_id
    ).order_by("id")

    return _compare_records(vw_result, sql_result)


def test_benthic_pit_su_sql_model():
    sql_result = (
        BenthicPITSUSQLModel.objects.all()
        .sql_table(project_id=benthic_pit_project_id)
        .order_by("id")
    )
    vw_result = BenthicPITSUView.objects.filter(
        project_id=benthic_pit_project_id
    ).order_by("id")

    return _compare_records(vw_result, sql_result)


def test_benthic_pit_se_sql_model():
    sql_result = (
        BenthicPITSESQLModel.objects.all()
        .sql_table(project_id=benthic_pit_project_id)
        .order_by("id")
    )
    vw_result = BenthicPITSEView.objects.filter(
        project_id=benthic_pit_project_id
    ).order_by("id")

    return _compare_records(vw_result, sql_result)


def test_benthic_lit_obs_sql_model():
    sql_result = (
        BenthicLITObsSQLModel.objects.all()
        .sql_table(project_id=benthic_lit_project_id)
        .order_by("id")
    )
    vw_result = BenthicLITObsView.objects.filter(
        project_id=benthic_lit_project_id
    ).order_by("id")

    return _compare_records(vw_result, sql_result)


def test_benthic_lit_su_sql_model():
    sql_result = (
        BenthicLITSUSQLModel.objects.all()
        .sql_table(project_id=benthic_lit_project_id)
        .order_by("id")
    )
    vw_result = BenthicLITSUView.objects.filter(
        project_id=benthic_lit_project_id
    ).order_by("id")

    return _compare_records(vw_result, sql_result)


def test_benthic_lit_se_sql_model():
    sql_result = (
        BenthicLITSESQLModel.objects.all()
        .sql_table(project_id=benthic_lit_project_id)
        .order_by("id")
    )
    vw_result = BenthicLITSEView.objects.filter(
        project_id=benthic_lit_project_id
    ).order_by("id")

    return _compare_records(vw_result, sql_result)


def test_habitat_complexity_obs_sql_model():
    sql_result = (
        HabitatComplexityObsSQLModel.objects.all()
        .sql_table(project_id=hb_project_id)
        .order_by("id")
    )
    vw_result = HabitatComplexityObsView.objects.filter(
        project_id=hb_project_id
    ).order_by("id")

    return _compare_records(vw_result, sql_result)


def test_habitat_complexity_su_sql_model():
    sql_result = (
        HabitatComplexitySUSQLModel.objects.all()
        .sql_table(project_id=hb_project_id)
        .order_by("id")
    )
    vw_result = HabitatComplexitySUView.objects.filter(
        project_id=hb_project_id
    ).order_by("id")

    return _compare_records(vw_result, sql_result)


def test_habitat_complexity_se_sql_model():
    sql_result = (
        HabitatComplexitySESQLModel.objects.all()
        .sql_table(project_id=hb_project_id)
        .order_by("id")
    )
    vw_result = HabitatComplexitySEView.objects.filter(
        project_id=hb_project_id
    ).order_by("id")

    return _compare_records(vw_result, sql_result)


def test_bleaching_colonies_obs_sql_model():
    sql_result = (
        BleachingQCColoniesBleachedObsSQLModel.objects.all()
        .sql_table(project_id=bleaching_project_id)
        .order_by("id")
    )
    vw_result = BleachingQCColoniesBleachedObsView.objects.filter(
        project_id=bleaching_project_id
    ).order_by("id")

    return _compare_records(vw_result, sql_result)


def test_bleaching_quad_percent_obs_sql_model():
    sql_result = (
        BleachingQCQuadratBenthicPercentObsSQLModel.objects.all()
        .sql_table(project_id=bleaching_project_id)
        .order_by("id")
    )
    vw_result = BleachingQCQuadratBenthicPercentObsView.objects.filter(
        project_id=bleaching_project_id
    ).order_by("id")

    return _compare_records(vw_result, sql_result)


def test_bleaching_qc_su_sql_model():
    sql_result = (
        BleachingQCSUSQLModel.objects.all()
        .sql_table(project_id=bleaching_project_id)
        .order_by("id")
    )
    vw_result = BleachingQCSUView.objects.filter(
        project_id=bleaching_project_id
    ).order_by("id")

    return _compare_records(vw_result, sql_result)


def test_bleaching_qc_se_sql_model():
    sql_result = (
        BleachingQCSESQLModel.objects.all()
        .sql_table(project_id=bleaching_project_id)
        .order_by("id")
    )
    vw_result = BleachingQCSEView.objects.filter(
        project_id=bleaching_project_id
    ).order_by("id")

    return _compare_records(vw_result, sql_result)


def _run_test(test_fx):
    try:
        sql_count, vw_count = test_fx()
        print(f"\033[92m{test_fx.__name__} - Pass\033[0m")
        print(f"\tsql_count: {sql_count}")
        print(f"\tvw_count: {vw_count}")
    except Exception as err:
        print(f"\033[91m{test_fx.__name__} - Fail\n{err}")
        print("------------------------------------------\033[0m")


def run():
    _run_test(test_belt_fish_obs_sql_model)
    _run_test(test_belt_fish_su_sql_model)
    _run_test(test_belt_fish_se_sql_model)

    _run_test(test_benthic_pit_obs_sql_model)
    _run_test(test_benthic_pit_su_sql_model)
    _run_test(test_benthic_pit_se_sql_model)

    _run_test(test_benthic_lit_obs_sql_model)
    _run_test(test_benthic_lit_su_sql_model)
    _run_test(test_benthic_lit_se_sql_model)

    _run_test(test_habitat_complexity_obs_sql_model)
    _run_test(test_habitat_complexity_su_sql_model)
    _run_test(test_habitat_complexity_se_sql_model)

    _run_test(test_bleaching_colonies_obs_sql_model)
    _run_test(test_bleaching_quad_percent_obs_sql_model)
    _run_test(test_bleaching_qc_su_sql_model)
    _run_test(test_bleaching_qc_se_sql_model)
