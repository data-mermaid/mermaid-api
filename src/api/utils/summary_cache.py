from django.db import transaction
from django.utils import timezone

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


def _set_created_on(created_on, records):
    for record in records:
        record.created_on = created_on


def _delete_existing_records(project_id, target_model_cls):
    target_model_cls.objects.filter(project_id=project_id).delete()


def _update_records(records, target_model_cls, created_on, skip_updates=False):
    if skip_updates or not records:
        return
    idx = 0
    while True:
        batch = records[idx : idx + BATCH_SIZE]
        _set_created_on(created_on, batch)
        if not batch:
            break
        target_model_cls.objects.bulk_create(batch, batch_size=BATCH_SIZE)
        idx += BATCH_SIZE


def _fetch_records(sql_model_cls, project_id):
    return list(sql_model_cls.objects.all().sql_table(project_id=project_id))


def _update_cache(
    project_id,
    obs_sql_model,
    obs_model,
    su_sql_model,
    su_model,
    se_sql_model,
    se_model,
    skip_updates,
):
    created_on = timezone.now()
    if skip_updates is not True:
        _delete_existing_records(project_id, obs_model)
        _delete_existing_records(project_id, su_model)
        _delete_existing_records(project_id, se_model)

    obs_records = _fetch_records(obs_sql_model, project_id)
    _update_records(obs_records, obs_model, created_on, skip_updates)

    su_records = _fetch_records(su_sql_model, project_id)
    _update_records(su_records, su_model, created_on, skip_updates)

    se_records = _fetch_records(se_sql_model, project_id)
    _update_records(se_records, se_model, created_on, skip_updates)


def _update_bleaching_qc_summary(project_id, skip_updates):
    created_on = timezone.now()

    if not skip_updates:
        _delete_existing_records(project_id, BleachingQCColoniesBleachedObsModel)
        _delete_existing_records(project_id, BleachingQCQuadratBenthicPercentObsModel)
        _delete_existing_records(project_id, BleachingQCSUModel)
        _delete_existing_records(project_id, BleachingQCSEModel)

    bleaching_colonies_obs = _fetch_records(BleachingQCColoniesBleachedObsSQLModel, project_id)
    bleaching_quad_percent_obs = _fetch_records(
        BleachingQCQuadratBenthicPercentObsSQLModel, project_id
    )
    _update_records(
        bleaching_colonies_obs,
        BleachingQCColoniesBleachedObsModel,
        created_on,
        skip_updates,
    )
    _update_records(
        bleaching_quad_percent_obs,
        BleachingQCQuadratBenthicPercentObsModel,
        created_on,
        skip_updates,
    )

    bleaching_su = _fetch_records(BleachingQCSUSQLModel, project_id)
    _update_records(bleaching_su, BleachingQCSUModel, created_on, skip_updates)

    bleaching_se = _fetch_records(BleachingQCSESQLModel, project_id)
    _update_records(bleaching_se, BleachingQCSEModel, created_on, skip_updates)


def _update_project_summary_sample_event(project_id, skip_test_project=True):
    if skip_test_project and Project.objects.filter(pk=project_id, status=Project.TEST).exists():
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
    print(f"project {project_id}")
    skip_updates = False
    if (
        skip_test_project is True
        and Project.objects.filter(id=project_id, status=Project.TEST).exists()
    ):
        skip_updates = True

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
                skip_updates,
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
                skip_updates,
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
                skip_updates,
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
                skip_updates,
            )

        if sample_unit is None or sample_unit == BLEACHINGQC_PROTOCOL:
            _update_bleaching_qc_summary(
                project_id,
                skip_updates,
            )

        if sample_unit is None or sample_unit == HABITATCOMPLEXITY_PROTOCOL:
            _update_cache(
                project_id,
                HabitatComplexityObsSQLModel,
                HabitatComplexityObsModel,
                HabitatComplexitySUSQLModel,
                HabitatComplexitySUModel,
                HabitatComplexitySESQLModel,
                HabitatComplexitySEModel,
                skip_updates,
            )

        _update_project_summary_sample_event(project_id)
