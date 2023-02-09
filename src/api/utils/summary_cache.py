from django.db import connection, transaction

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


def _update_records(sql_model_cls, model_cls, project_id, generate_id=True):
    
    cur = connection.cursor()
    try:
        qry = sql_model_cls.objects.all().sql_table(project_id=project_id).query
        template_sql, params = qry.sql_with_params()
        sql = cur.mogrify(template_sql, params)

        insert_columns = ", ".join([f'"{f.get_attname_column()[1]}"' for f in sql_model_cls._meta.get_fields()])
        if generate_id:
            select_columns = ", ".join([f'"{f.get_attname_column()[1]}"' for f in sql_model_cls._meta.get_fields() if f.primary_key is False])
            select_columns = f"gen_random_uuid() AS id, {select_columns}"
        else:
            select_columns = insert_columns
        
    
        resovled_sql = sql.decode()
        delete_sql = f"DELETE FROM {model_cls._meta.db_table} WHERE project_id = '{project_id}';"
        insert_sql = f"INSERT INTO {model_cls._meta.db_table} ({insert_columns}) SELECT {select_columns} FROM ({resovled_sql}) AS foo;"
        cur.execute(delete_sql + insert_sql)
    except Exception as err:
        new_cur = connection.cursor()
        new_cur.execute(f"SELECT {select_columns} FROM ({resovled_sql}) AS foo");
        print(",".join([elt[0] for elt in new_cur.description]))
        for row in new_cur:
            print(f"\t {row}")
        
        print(f"--------{project_id}----------")
        new_cur.close()
        raise
    finally:
        cur.close()


def _update_cache(
    project_id, obs_sql_model, obs_model, su_sql_model, su_model, se_sql_model, se_model
):
    _update_records(obs_sql_model, obs_model, project_id)
    _update_records(su_sql_model, su_model, project_id)
    _update_records(se_sql_model, se_model, project_id)


def _update_bleaching_qc_summary(project_id):

    _update_records(BleachingQCColoniesBleachedObsSQLModel, BleachingQCColoniesBleachedObsModel, project_id)
    _update_records(
        BleachingQCQuadratBenthicPercentObsSQLModel, BleachingQCQuadratBenthicPercentObsModel, project_id
    )
    _update_records(BleachingQCSUSQLModel, BleachingQCSUModel, project_id)
    _update_records(BleachingQCSESQLModel, BleachingQCSEModel, project_id)


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
    # with transaction.atomic():
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
