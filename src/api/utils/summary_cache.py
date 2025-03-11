from django.db import connection, transaction
from django.db.utils import DataError, IntegrityError
from django.utils import timezone

from ..exceptions import UpdateSummariesException, check_uuid
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
    SummaryCacheQueue,
    SummarySampleEventModel,
    SummarySampleEventSQLModel,
    UnrestrictedProjectSummarySampleEvent,
)
from ..resources.summary_sample_event import SummarySampleEventSerializer
from ..utils.project import suggested_citation as get_suggested_citation
from ..utils.timer import timing

BATCH_SIZE = 1000
BUFFER_TIME = 3  # in seconds


# -- SQL Update ---
def _convert_to_sql(queryset):
    with connection.cursor() as cur:
        qry = queryset.query
        template_sql, params = qry.sql_with_params()
        sql = cur.mogrify(template_sql, params)

    return sql.decode()


def _columns(model_cls):
    return [field.name for field in model_cls._meta.fields]


def _insert(model_cls, sql, suggested_citation):
    cols = _columns(model_cls)
    extras = {
        "created_on": "now()",
        "suggested_citation": f"'{suggested_citation}'",
    }

    insert_cols = ", ".join(cols)

    # update any columns from cols that are in extras
    updated_cols = []
    for col in cols:
        if col not in extras:
            updated_cols.append(col)
        else:
            updated_cols.append(f"{extras[col]} AS {col}")

    select_cols = ", ".join(updated_cols)

    return f"""
        INSERT INTO {model_cls._meta.db_table}
        ({insert_cols})
        SELECT {select_cols} FROM ({sql}) AS foo;
    """


def _delete(model_cls, project_id):
    return f"DELETE FROM {model_cls._meta.db_table} WHERE project_id = '{project_id}';"


def _sql_update_cache(
    project_id,
    obs_sql_model,
    obs_model,
    su_sql_model,
    su_model,
    se_sql_model,
    se_model,
    skip_updates,
):
    suggested_citation = _get_suggested_citation(project_id)

    sql = []
    if skip_updates is not True:
        sql.append(_delete(obs_model, project_id))
        sql.append(_delete(su_model, project_id))
        sql.append(_delete(se_model, project_id))

    obs_sql = _convert_to_sql(obs_sql_model.objects.all().sql_table(project_id=project_id))
    sql.append(_insert(obs_model, obs_sql, suggested_citation))

    su_sql = _convert_to_sql(su_sql_model.objects.all().sql_table(project_id=project_id))
    sql.append(_insert(su_model, su_sql, suggested_citation))

    se_sql = _convert_to_sql(se_sql_model.objects.all().sql_table(project_id=project_id))
    sql.append(_insert(se_model, se_sql, suggested_citation))

    with connection.cursor() as cur:
        cur.execute("".join(sql))


def _sql_update_bleaching_qc_summary(
    project_id,
    skip_updates,
):
    suggested_citation = _get_suggested_citation(project_id)

    sql = []
    if not skip_updates:
        sql.append(_delete(BleachingQCColoniesBleachedObsModel, project_id))
        sql.append(_delete(BleachingQCQuadratBenthicPercentObsModel, project_id))
        sql.append(_delete(BleachingQCSUModel, project_id))
        sql.append(_delete(BleachingQCSEModel, project_id))

    colonies_obs_sql = _convert_to_sql(
        BleachingQCColoniesBleachedObsSQLModel.objects.all().sql_table(project_id=project_id)
    )
    sql.append(_insert(BleachingQCColoniesBleachedObsModel, colonies_obs_sql, suggested_citation))

    colonies_obs_sql = _convert_to_sql(
        BleachingQCQuadratBenthicPercentObsSQLModel.objects.all().sql_table(project_id=project_id)
    )
    sql.append(
        _insert(BleachingQCQuadratBenthicPercentObsModel, colonies_obs_sql, suggested_citation)
    )

    su_sql = _convert_to_sql(BleachingQCSUSQLModel.objects.all().sql_table(project_id=project_id))
    sql.append(_insert(BleachingQCSUModel, su_sql, suggested_citation))

    se_sql = _convert_to_sql(BleachingQCSESQLModel.objects.all().sql_table(project_id=project_id))
    sql.append(_insert(BleachingQCSEModel, se_sql, suggested_citation))

    with connection.cursor() as cur:
        cur.execute("".join(sql))


def _sql_update_project_summary_sample_event(project_id, skip_updates):
    suggested_citation = _get_suggested_citation(project_id)
    sql = []
    if skip_updates is not True:
        sql.append(_delete(SummarySampleEventModel, project_id))

    sse_sql = _convert_to_sql(
        SummarySampleEventSQLModel.objects.all().sql_table(project_id=project_id)
    )
    sql.append(_insert(SummarySampleEventModel, sse_sql, suggested_citation))

    with connection.cursor() as cur:
        cur.execute("".join(sql))


def _get_suggested_citation(project_id):
    suggested_citation = ""
    project = Project.objects.get_or_none(id=project_id)
    if project:
        suggested_citation = get_suggested_citation(project)
    return suggested_citation


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
        suggested_citation = _get_suggested_citation(project_id)
        for record in records:
            record["suggested_citation"] = suggested_citation

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
            project_includes_gfcr=project.includes_gfcr,
            suggested_citation=suggested_citation,
            data_policy_beltfish=data_policies.get(
                project.data_policy_beltfish, Project.data_policy_beltfish.field.default
            ),
            data_policy_benthiclit=data_policies.get(
                project.data_policy_benthiclit, Project.data_policy_benthiclit.field.default
            ),
            data_policy_benthicpit=data_policies.get(
                project.data_policy_benthicpit, Project.data_policy_benthicpit.field.default
            ),
            data_policy_habitatcomplexity=data_policies.get(
                project.data_policy_habitatcomplexity,
                Project.data_policy_habitatcomplexity.field.default,
            ),
            data_policy_bleachingqc=data_policies.get(
                project.data_policy_bleachingqc, Project.data_policy_bleachingqc.field.default
            ),
            data_policy_benthicpqt=data_policies.get(
                project.data_policy_benthicpqt, Project.data_policy_benthicpqt.field.default
            ),
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


def add_project_to_queue(project_id, skip_test_project=False):
    check_uuid(project_id)

    with connection.cursor() as cursor:
        if (
            skip_test_project
            and Project.objects.filter(id=project_id, status=Project.TEST).exists()
        ):
            print(f"Skipping test project {project_id}")
            return

        scq_qry = SummaryCacheQueue.objects.filter(
            project_id=project_id, processing=False, attempts=3
        )
        if scq_qry.exists():
            scq_qry.delete()

        sql = f"""
        INSERT INTO "{SummaryCacheQueue._meta.db_table}"
        ("project_id", "processing", "attempts", "created_on")
        VALUES (%s, false, 0, now())
        ON CONFLICT (project_id, processing)
        DO NOTHING;
        """

        cursor.execute(sql, [project_id])


@timing
def update_summary_cache(project_id, sample_unit=None, skip_test_project=False):
    skip_updates = False
    if (
        skip_test_project is True
        and Project.objects.filter(id=project_id, status=Project.TEST).exists()
    ):
        skip_updates = True

    try:
        with transaction.atomic():
            if sample_unit is None or sample_unit == FISHBELT_PROTOCOL:
                _sql_update_cache(
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
                _sql_update_cache(
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
                _sql_update_cache(
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
                _sql_update_cache(
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
                _sql_update_bleaching_qc_summary(
                    project_id,
                    skip_updates,
                )

            if sample_unit is None or sample_unit == HABITATCOMPLEXITY_PROTOCOL:
                _sql_update_cache(
                    project_id,
                    HabitatComplexityObsSQLModel,
                    HabitatComplexityObsModel,
                    HabitatComplexitySUSQLModel,
                    HabitatComplexitySUModel,
                    HabitatComplexitySESQLModel,
                    HabitatComplexitySEModel,
                    skip_updates,
                )

            _sql_update_project_summary_sample_event(project_id, skip_updates)

            timestamp = timezone.now()
            _update_unrestricted_project_summary_sample_events(project_id, timestamp, skip_updates)
            _update_restricted_project_summary_sample_events(project_id, timestamp, skip_updates)

    except (DataError, IntegrityError) as e:
        raise UpdateSummariesException(message=str(e)) from e
