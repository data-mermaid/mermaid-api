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
    SampleEvent,
    SummarySampleEventModel,
    SummarySampleEventSQLModel,
)
from ..utils.timer import timing

BATCH_SIZE = 1000


def _set_created_on(created_on, records):
    for record in records:
        record.created_on = created_on


def _update_records(project_id, records, target_model_cls, created_on, skip_updates=False):
    target_model_cls.objects.filter(project_id=project_id).delete()
    if skip_updates:
        return
    idx = 0
    while True:
        batch = records[idx : idx + BATCH_SIZE]
        _set_created_on(created_on, batch)
        if not batch:
            break
        target_model_cls.objects.bulk_create(batch, batch_size=BATCH_SIZE)
        idx += BATCH_SIZE


def _fetch_records(sql_model_cls, project_id, sample_event_ids=None):
    return list(
        sql_model_cls.objects.all().sql_table(
            project_id=project_id, sample_event_ids=sample_event_ids
        )
    )


def _update_cache(
    project_id,
    sample_event_ids_set,
    obs_sql_model,
    obs_model,
    su_sql_model,
    su_model,
    se_sql_model,
    se_model,
    skip_updates,
):
    created_on = timezone.now()
    for sample_event_ids in sample_event_ids_set:
        obs_records = _fetch_records(obs_sql_model, project_id, sample_event_ids)
        _update_records(project_id, obs_records, obs_model, created_on, skip_updates)

        su_records = _fetch_records(su_sql_model, project_id)
        _update_records(project_id, su_records, su_model, created_on, skip_updates)

        se_records = _fetch_records(se_sql_model, project_id)
        _update_records(project_id, se_records, se_model, created_on, skip_updates)


def _update_bleaching_qc_summary(project_id, sample_event_ids_set, skip_updates):
    created_on = timezone.now()
    for sample_event_ids in sample_event_ids_set:
        bleaching_colonies_obs = _fetch_records(
            BleachingQCColoniesBleachedObsSQLModel, project_id, sample_event_ids
        )
        bleaching_quad_percent_obs = _fetch_records(
            BleachingQCQuadratBenthicPercentObsSQLModel, project_id, sample_event_ids
        )

        _update_records(
            project_id,
            bleaching_colonies_obs,
            BleachingQCColoniesBleachedObsModel,
            created_on,
            skip_updates,
        )
        _update_records(
            project_id,
            bleaching_quad_percent_obs,
            BleachingQCQuadratBenthicPercentObsModel,
            created_on,
            skip_updates,
        )

        bleaching_su = _fetch_records(BleachingQCSUSQLModel, project_id)
        _update_records(project_id, bleaching_su, BleachingQCSUModel, created_on, skip_updates)

        bleaching_se = _fetch_records(BleachingQCSESQLModel, project_id)
        _update_records(project_id, bleaching_se, BleachingQCSEModel, created_on, skip_updates)


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


def _get_sample_event_ids_set(project_id):
    sample_events = list(SampleEvent.objects.filter(site__project_id=project_id))
    chunks = 10
    return [
        ",".join(f"'{se.id}'::uuid" for se in sample_events[i : i + chunks])
        for i in range(0, len(sample_events), chunks)
    ]


@timing
def update_summary_cache(project_id, sample_unit=None, skip_test_project=True):
    skip_updates = False
    if (
        skip_test_project is True
        and Project.objects.filter(id=project_id, status=Project.TEST).exists()
    ):
        skip_updates = True

    sample_event_ids = _get_sample_event_ids_set(project_id)

    with transaction.atomic():
        if sample_unit is None or sample_unit == FISHBELT_PROTOCOL:
            _update_cache(
                project_id,
                sample_event_ids,
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
                sample_event_ids,
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
                sample_event_ids,
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
                sample_event_ids,
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
                sample_event_ids,
                skip_updates,
            )

        if sample_unit is None or sample_unit == HABITATCOMPLEXITY_PROTOCOL:
            _update_cache(
                project_id,
                sample_event_ids,
                HabitatComplexityObsSQLModel,
                HabitatComplexityObsModel,
                HabitatComplexitySUSQLModel,
                HabitatComplexitySUModel,
                HabitatComplexitySESQLModel,
                HabitatComplexitySEModel,
                skip_updates,
            )

        _update_project_summary_sample_event(project_id)
