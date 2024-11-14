from datetime import timedelta

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
    ProjectProfile,
    RestrictedProjectSummarySampleEvent,
    SummarySampleEventModel,
    SummarySampleEventSQLModel,
    UnrestrictedProjectSummarySampleEvent,
)
from ..resources.summary_sample_event import SummarySampleEventSerializer
from ..utils.timer import timing

BATCH_SIZE = 1000
BUFFER_TIME = 3  # in seconds


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


def _is_update_required(timestamp, project_id, model_cls):
    if timestamp is None:
        return True

    ts = timestamp - timedelta(seconds=BUFFER_TIME)
    rec = model_cls.objects.filter(project_id=project_id).order_by("-created_on").first()

    if rec is None:
        return True

    return rec.created_on > ts


def _update_cache(
    project_id,
    obs_sql_model,
    obs_model,
    su_sql_model,
    su_model,
    se_sql_model,
    se_model,
    skip_updates,
    timestamp=None,
):
    if not _is_update_required(timestamp, project_id, obs_model):
        return

    if skip_updates is not True:
        _delete_existing_records(project_id, obs_model)
        _delete_existing_records(project_id, su_model)
        _delete_existing_records(project_id, se_model)

    obs_records = _fetch_records(obs_sql_model, project_id)
    su_records = _fetch_records(su_sql_model, project_id)
    se_records = _fetch_records(se_sql_model, project_id)

    created_on = timezone.now()

    _update_records(obs_records, obs_model, created_on, skip_updates)
    _update_records(su_records, su_model, created_on, skip_updates)
    _update_records(se_records, se_model, created_on, skip_updates)


def _update_bleaching_qc_summary(
    project_id,
    skip_updates,
    timestamp=None,
):
    created_on = timezone.now()

    if not _is_update_required(timestamp, project_id, BleachingQCColoniesBleachedObsModel):
        return

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


def _update_project_summary_sample_events(
    proj_summary_se_model, project_id, timestamp, skip_test_project=True, has_access="false"
):
    if skip_test_project and Project.objects.filter(pk=project_id, status=Project.TEST).exists():
        proj_summary_se_model.objects.filter(project_id=project_id).delete()
        return
    project = Project.objects.get_or_none(pk=project_id)
    if project is not None:
        qs = SummarySampleEventSQLModel.objects.all().sql_table(
            project_id=project_id, has_access=has_access
        )
        records = SummarySampleEventSerializer(qs, many=True).data

        proj_summary_se_model.objects.filter(project_id=project_id).delete()
        tags = [{"id": str(t.pk), "name": t.name} for t in project.tags.all()]
        admins = project.profiles.filter(role=ProjectProfile.ADMIN)
        project_admins = [{"id": str(pa.pk), "name": pa.profile_name} for pa in admins]
        data_policies = dict(Project.DATA_POLICIES)

        proj_summary_se_model.objects.create(
            project_id=project_id,
            project_name=project.name,
            project_admins=project_admins,
            project_notes=project.notes,
            data_policy_beltfish=data_policies.get(project.data_policy_beltfish),
            data_policy_benthiclit=data_policies.get(project.data_policy_benthiclit),
            data_policy_benthicpit=data_policies.get(project.data_policy_benthicpit),
            data_policy_habitatcomplexity=data_policies.get(project.data_policy_habitatcomplexity),
            data_policy_bleachingqc=data_policies.get(project.data_policy_bleachingqc),
            data_policy_benthicpqt=data_policies.get(project.data_policy_benthicpqt),
            tags=tags,
            records=records,
            created_on=timestamp,
        )


def _update_restricted_project_summary_sample_events(project_id, timestamp, skip_test_project=True):
    _update_project_summary_sample_events(
        RestrictedProjectSummarySampleEvent,
        project_id,
        timestamp,
        skip_test_project,
        has_access="true",
    )


def _update_unrestricted_project_summary_sample_events(
    project_id, timestamp, skip_test_project=True
):
    _update_project_summary_sample_events(
        UnrestrictedProjectSummarySampleEvent, project_id, timestamp, skip_test_project
    )


@timing
def update_summary_cache(project_id, sample_unit=None, skip_test_project=False, timestamp=None):
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
                timestamp,
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
                timestamp,
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
                timestamp,
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
                timestamp,
            )

        if sample_unit is None or sample_unit == BLEACHINGQC_PROTOCOL:
            _update_bleaching_qc_summary(
                project_id,
                skip_updates,
                timestamp,
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
                timestamp,
            )

        _update_project_summary_sample_event(project_id, skip_updates)
        timestamp = timezone.now()
        _update_unrestricted_project_summary_sample_events(project_id, timestamp, skip_updates)
        _update_restricted_project_summary_sample_events(project_id, timestamp, skip_updates)
