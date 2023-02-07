from django.db import transaction

from ..models import (
    BENTHICLIT_PROTOCOL,
    BENTHICPIT_PROTOCOL,
    BENTHICPQT_PROTOCOL,
    BLEACHINGQC_PROTOCOL,
    FISHBELT_PROTOCOL,
    HABITATCOMPLEXITY_PROTOCOL,
    BeltFishObsModel,
    BeltFishObsSQLModel,
    BeltFishSEModel,
    BeltFishSESQLModel,
    BeltFishSUModel,
    BeltFishSUSQLModel,
    BenthicLITObsModel,
    BenthicLITObsSQLModel,
    BenthicLITSEModel,
    BenthicLITSESQLModel,
    BenthicLITSUModel,
    BenthicLITSUSQLModel,
    BenthicPhotoQuadratTransectObsModel,
    BenthicPhotoQuadratTransectObsSQLModel,
    BenthicPhotoQuadratTransectSEModel,
    BenthicPhotoQuadratTransectSESQLModel,
    BenthicPhotoQuadratTransectSUModel,
    BenthicPhotoQuadratTransectSUSQLModel,
    BenthicPITObsModel,
    BenthicPITObsSQLModel,
    BenthicPITSEModel,
    BenthicPITSESQLModel,
    BenthicPITSUModel,
    BenthicPITSUSQLModel,
    BleachingQCColoniesBleachedObsModel,
    BleachingQCColoniesBleachedObsSQLModel,
    BleachingQCQuadratBenthicPercentObsModel,
    BleachingQCQuadratBenthicPercentObsSQLModel,
    BleachingQCSEModel,
    BleachingQCSESQLModel,
    BleachingQCSUModel,
    BleachingQCSUSQLModel,
    HabitatComplexityObsModel,
    HabitatComplexityObsSQLModel,
    HabitatComplexitySEModel,
    HabitatComplexitySESQLModel,
    HabitatComplexitySUModel,
    HabitatComplexitySUSQLModel,
    Project,
    SummarySampleEventModel,
    SummarySampleEventSQLModel,
)
from ..utils.timer import timing

BATCH_SIZE = 1000


def _update_records(records, target_model_cls):
    target_model_cls.objects.all().delete()
    idx = 0
    while True:
        batch = records[idx : idx + BATCH_SIZE]
        if not batch:
            break
        target_model_cls.objects.bulk_create(batch, batch_size=BATCH_SIZE)
        idx += BATCH_SIZE


def _fetch_records(sql_model_cls, project_id):
    return list(sql_model_cls.objects.all().sql_table(project_id=project_id))


def _update_cache(
    project_id, obs_sql_model, obs_model, su_sql_model, su_model, se_sql_model, se_model
):
    obs_records = _fetch_records(obs_sql_model, project_id)
    _update_records(obs_records, obs_model)

    su_records = _fetch_records(su_sql_model, project_id)
    _update_records(su_records, su_model)

    se_records = _fetch_records(se_sql_model, project_id)
    _update_records(se_records, se_model)


def _update_bleaching_qc_summary(project_id):
    bleaching_colonies_obs = _fetch_records(
        BleachingQCColoniesBleachedObsSQLModel, project_id
    )
    bleaching_quad_percent_obs = _fetch_records(
        BleachingQCQuadratBenthicPercentObsSQLModel, project_id
    )

    _update_records(bleaching_colonies_obs, BleachingQCColoniesBleachedObsModel)
    _update_records(
        bleaching_quad_percent_obs, BleachingQCQuadratBenthicPercentObsModel
    )

    bleaching_su = _fetch_records(BleachingQCSUSQLModel, project_id)
    _update_records(bleaching_su, BleachingQCSUModel)

    bleaching_se = _fetch_records(BleachingQCSESQLModel, project_id)
    _update_records(bleaching_se, BleachingQCSEModel)


def _update_project_summary_sample_event(project_id, skip_test_project=True):
    if (
        skip_test_project
        and Project.objects.filter(pk=project_id, status=Project.TEST).exists()
    ):
        SummarySampleEventModel.objects.filter(project_id=project_id).delete()
        return

    summary_sample_events = list(
        SummarySampleEventSQLModel.objects.all().sql_table(project_id=project_id)
    )
    SummarySampleEventModel.objects.filter(project_id=project_id).delete()
    for record in summary_sample_events:
        values = {
            field.name: getattr(record, field.name)
            for field in SummarySampleEventModel._meta.fields
        }
        SummarySampleEventModel.objects.create(**values)


@timing
def update_summary_cache(project_id, sample_unit=None, skip_test_project=True):
    if (
        skip_test_project is True
        and Project.objects.filter(id=project_id, status=Project.TEST).exists()
    ):
        return

    with transaction.atomic():
        if sample_unit is None or sample_unit == FISHBELT_PROTOCOL:
            _update_cache(
                project_id,
                BeltFishObsSQLModel,
                BeltFishObsModel,
                BeltFishSUSQLModel,
                BeltFishSUModel,
                BeltFishSESQLModel,
                BeltFishSEModel,
            )

        if sample_unit is None or sample_unit == BENTHICLIT_PROTOCOL:
            _update_cache(
                project_id,
                BenthicLITObsSQLModel,
                BenthicLITObsModel,
                BenthicLITSUSQLModel,
                BenthicLITSUModel,
                BenthicLITSESQLModel,
                BenthicLITSEModel,
            )

        if sample_unit is None or sample_unit == BENTHICPIT_PROTOCOL:
            _update_cache(
                project_id,
                BenthicPITObsSQLModel,
                BenthicPITObsModel,
                BenthicPITSUSQLModel,
                BenthicPITSUModel,
                BenthicPITSESQLModel,
                BenthicPITSEModel,
            )

        if sample_unit is None or sample_unit == BENTHICPQT_PROTOCOL:
            _update_cache(
                project_id,
                BenthicPhotoQuadratTransectObsSQLModel,
                BenthicPhotoQuadratTransectObsModel,
                BenthicPhotoQuadratTransectSUSQLModel,
                BenthicPhotoQuadratTransectSUModel,
                BenthicPhotoQuadratTransectSESQLModel,
                BenthicPhotoQuadratTransectSEModel,
            )

        if sample_unit is None or sample_unit == BLEACHINGQC_PROTOCOL:
            _update_bleaching_qc_summary(project_id)

        if sample_unit is None or sample_unit == HABITATCOMPLEXITY_PROTOCOL:
            _update_cache(
                project_id,
                HabitatComplexityObsSQLModel,
                HabitatComplexityObsModel,
                HabitatComplexitySUSQLModel,
                HabitatComplexitySUModel,
                HabitatComplexitySESQLModel,
                HabitatComplexitySEModel,
            )

        _update_project_summary_sample_event(project_id)
