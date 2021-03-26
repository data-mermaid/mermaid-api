from django.contrib.gis.db import models
from django.contrib.postgres.fields import JSONField
from django.utils.translation import ugettext_lazy as _

from sqltables import SQLTableArg, SQLTableManager
from .base import BaseSQLModel, BaseSUSQLModel, sample_event_sql_template


class BleachingQCColoniesBleachedObsSQLModel(BaseSUSQLModel):
    _se_fields = ", ".join([f"se.{f}" for f in BaseSUSQLModel.se_fields])
    _su_fields = BaseSUSQLModel.su_fields_sql

    sql = f"""
        SELECT
            o.id,
            { _se_fields },
            { _su_fields },
            se.data_policy_bleachingqc,
            su.quadrat_size,
            b.name AS benthic_attribute,
            gf.name AS growth_form,
            o.count_normal,
            o.count_pale,
            o.count_20,
            o.count_50,
            o.count_80,
            o.count_100,
            o.count_dead
        FROM
            obs_colonies_bleached o
            JOIN benthic_attribute b ON o.attribute_id = b.id
            LEFT JOIN growth_form gf ON o.growth_form_id = gf.id
            JOIN transectmethod_bleaching_quadrat_collection tt ON o.bleachingquadratcollection_id = tt.transectmethod_ptr_id
            JOIN quadrat_collection su ON tt.quadrat_id = su.id
            LEFT JOIN api_current c ON su.current_id = c.id
            LEFT JOIN api_tide t ON su.tide_id = t.id
            LEFT JOIN api_visibility v ON su.visibility_id = v.id
            LEFT JOIN api_relativedepth r ON su.relative_depth_id = r.id
            JOIN (
                SELECT
                    tt_1.quadrat_id,
                    jsonb_agg(
                        jsonb_build_object(
                            'id',
                            p.id,
                            'name',
                            (
                                COALESCE(p.first_name, '' :: character varying) :: text || ' ' :: text
                            ) || COALESCE(p.last_name, '' :: character varying) :: text
                        )
                    ) AS observers
                FROM
                    observer o1
                    JOIN profile p ON o1.profile_id = p.id
                    JOIN transectmethod tm ON o1.transectmethod_id = tm.id
                    JOIN transectmethod_bleaching_quadrat_collection tt_1 ON tm.id = tt_1.transectmethod_ptr_id
                GROUP BY
                    tt_1.quadrat_id
            ) observers ON su.id = observers.quadrat_id
            JOIN ({ sample_event_sql_template }) se ON su.sample_event_id = se.sample_event_id
    """

    sql_args = dict(project_id=SQLTableArg(required=True))

    objects = SQLTableManager()

    sample_unit_id = models.UUIDField()
    quadrat_size = models.DecimalField(decimal_places=2, max_digits=6)
    benthic_attribute = models.CharField(max_length=100)
    growth_form = models.CharField(max_length=100)
    count_normal = models.PositiveSmallIntegerField(verbose_name="normal", default=0)
    count_pale = models.PositiveSmallIntegerField(verbose_name="pale", default=0)
    count_20 = models.PositiveSmallIntegerField(
        verbose_name="0-20% bleached", default=0
    )
    count_50 = models.PositiveSmallIntegerField(
        verbose_name="20-50% bleached", default=0
    )
    count_80 = models.PositiveSmallIntegerField(
        verbose_name="50-80% bleached", default=0
    )
    count_100 = models.PositiveSmallIntegerField(
        verbose_name="80-100% bleached", default=0
    )
    count_dead = models.PositiveSmallIntegerField(
        verbose_name="recently dead", default=0
    )
    data_policy_bleachingqc = models.CharField(max_length=50)

    class Meta:
        db_table = "bleachingqc_colonies_bleached_obs_sm"
        managed = False


class BleachingQCQuadratBenthicPercentObsSQLModel(BaseSUSQLModel):
    # Unique combination of these fields defines a single (pseudo) sample unit. All other fields are aggregated.
    su_fields = BaseSUSQLModel.se_fields + [
        "depth",
        "quadrat_size",
        "data_policy_bleachingqc",
    ]

    _se_fields = ", ".join([f"se.{f}" for f in BaseSUSQLModel.se_fields])
    _su_fields = BaseSUSQLModel.su_fields_sql

    sql = f"""
        SELECT o.id,
        {_se_fields},
        {_su_fields},
        se.data_policy_bleachingqc,
        su.quadrat_size,
        o.quadrat_number,
        o.percent_hard,
        o.percent_soft,
        o.percent_algae
        FROM
        obs_quadrat_benthic_percent o
        JOIN transectmethod_bleaching_quadrat_collection tt ON o.bleachingquadratcollection_id = tt.transectmethod_ptr_id
        JOIN quadrat_collection su ON tt.quadrat_id = su.id
        LEFT JOIN api_current c ON su.current_id = c.id
        LEFT JOIN api_tide t ON su.tide_id = t.id
        LEFT JOIN api_visibility v ON su.visibility_id = v.id
        LEFT JOIN api_relativedepth r ON su.relative_depth_id = r.id
        JOIN (
            SELECT tt_1.quadrat_id,
            jsonb_agg(
            jsonb_build_object(
                'id', p.id,
                'name',
                (COALESCE(p.first_name, ''::character varying)::text || ' '::text) ||
                COALESCE(p.last_name, ''::character varying)::text
            )
            ) AS observers
            FROM
            observer o1
            JOIN profile p ON o1.profile_id = p.id
            JOIN transectmethod tm ON o1.transectmethod_id = tm.id
            JOIN transectmethod_bleaching_quadrat_collection tt_1 ON tm.id = tt_1.transectmethod_ptr_id
            GROUP BY tt_1.quadrat_id
        ) observers ON su.id = observers.quadrat_id
        JOIN ({sample_event_sql_template}) se ON su.sample_event_id = se.sample_event_id
    """

    sql_args = dict(project_id=SQLTableArg(required=True))

    objects = SQLTableManager()

    sample_unit_id = models.UUIDField()
    quadrat_size = models.DecimalField(decimal_places=2, max_digits=6)
    quadrat_number = models.PositiveSmallIntegerField(verbose_name="quadrat number")
    percent_hard = models.PositiveSmallIntegerField(
        verbose_name="hard coral, % cover", default=0
    )
    percent_soft = models.PositiveSmallIntegerField(
        verbose_name="soft coral, % cover", default=0
    )
    percent_algae = models.PositiveSmallIntegerField(
        verbose_name="macroalgae, % cover", default=0
    )
    data_policy_bleachingqc = models.CharField(max_length=50)

    class Meta:
        db_table = "bleachingqc_quadrat_benthic_percent_obs_sm"
        managed = False


class BleachingQCSUSQLModel(BaseSUSQLModel):
    # Unique combination of these fields defines a single (pseudo) sample unit. All other fields are aggregated.
    su_fields = BaseSUSQLModel.se_fields + [
        "depth",
        "quadrat_size",
        "data_policy_bleachingqc",
    ]

    _su_fields = ", ".join(su_fields)
    _su_fields_qualified = ", ".join(
        [f"bleachingqc_colonies_bleached_obs.{f}" for f in su_fields]
    )
    _agg_su_fields = ", ".join(BaseSUSQLModel.agg_su_fields)
    _su_aggfields_sql = BaseSUSQLModel.su_aggfields_sql

    # SU fields and observers pieces both rely on being the same for both types of QC observations
    sql = f"""
        WITH bleachingqc_colonies_bleached_obs AS (
            {BleachingQCColoniesBleachedObsSQLModel.sql}
        ),
        bleachingqc_quadrat_benthic_percent_obs AS (
            {BleachingQCQuadratBenthicPercentObsSQLModel.sql}
        )
        SELECT NULL AS id,
        uuid_generate_v4() AS pseudosu_id,
        {_su_fields},
        bleachingqc_su.{_agg_su_fields},
        count_genera,
        count_total,
        percent_normal,
        percent_pale,
        percent_bleached,
        quadrat_count,
        percent_hard_avg,
        percent_soft_avg,
        percent_algae_avg
        FROM (
            SELECT 
            jsonb_agg(DISTINCT sample_unit_id) AS sample_unit_ids,
            {_su_fields_qualified},
            {_su_aggfields_sql},
            COUNT(DISTINCT benthic_attribute) AS count_genera,
            SUM(count_normal + count_pale + count_20 + count_50 + count_80 + count_100 + count_dead) AS count_total,
            ROUND(100 *
                (SUM(count_normal)::decimal /
                CASE WHEN SUM(count_normal + count_pale + count_20 + count_50 + count_80 + count_100 + count_dead) = 0 THEN 1
                ELSE SUM(count_normal + count_pale + count_20 + count_50 + count_80 + count_100 + count_dead) END
                )
            , 1) AS percent_normal,
            ROUND(100 *
                (SUM(count_pale)::decimal /
                CASE WHEN SUM(count_normal + count_pale + count_20 + count_50 + count_80 + count_100 + count_dead) = 0 THEN 1
                ELSE SUM(count_normal + count_pale + count_20 + count_50 + count_80 + count_100 + count_dead) END
                )
            , 1) AS percent_pale,
            ROUND(100 *
                (SUM(count_20 + count_50 + count_80 + count_100 + count_dead)::decimal /
                CASE WHEN SUM(count_normal + count_pale + count_20 + count_50 + count_80 + count_100 + count_dead) = 0 THEN 1
                ELSE SUM(count_normal + count_pale + count_20 + count_50 + count_80 + count_100 + count_dead) END
                )
            , 1) AS percent_bleached

            FROM bleachingqc_colonies_bleached_obs
            GROUP BY 
            {_su_fields_qualified}
        ) bleachingqc_su

        INNER JOIN (
            SELECT jsonb_agg(DISTINCT sample_unit_id) AS sample_unit_ids,
            COUNT(quadrat_number) AS quadrat_count,
            round(AVG(percent_hard), 1) AS percent_hard_avg,
            round(AVG(percent_soft), 1) AS percent_soft_avg,
            round(AVG(percent_algae), 1) AS percent_algae_avg
            FROM bleachingqc_quadrat_benthic_percent_obs
            GROUP BY depth, quadrat_size, sample_event_id
        ) bp ON bleachingqc_su.sample_unit_ids = bp.sample_unit_ids

        INNER JOIN (
            SELECT jsonb_agg(DISTINCT sample_unit_id) AS sample_unit_ids,
            jsonb_agg(DISTINCT observer) AS observers

            FROM (
                SELECT sample_unit_id,
                {_su_fields},
                jsonb_array_elements(observers) AS observer
                FROM bleachingqc_colonies_bleached_obs
                GROUP BY {_su_fields}, sample_unit_id,
                observers
            ) bleachingqc_obs_obs
            GROUP BY {_su_fields}
        ) bleachingqc_observers
        ON (bleachingqc_su.sample_unit_ids = bleachingqc_observers.sample_unit_ids)
    """

    sql_args = dict(project_id=SQLTableArg(required=True))

    objects = SQLTableManager()

    sample_unit_ids = JSONField()
    quadrat_size = models.DecimalField(decimal_places=2, max_digits=6)
    count_genera = models.PositiveSmallIntegerField(default=0)
    count_total = models.PositiveSmallIntegerField(default=0)
    percent_normal = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    percent_pale = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    percent_bleached = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    quadrat_count = models.PositiveSmallIntegerField(default=0)
    percent_hard_avg = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    percent_soft_avg = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    percent_algae_avg = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    data_policy_bleachingqc = models.CharField(max_length=50)

    class Meta:
        db_table = "bleachingqc_su_sm"
        managed = False


class BleachingQCSESQLModel(BaseSQLModel):

    _se_fields = ", ".join([f"bleachingqc_su.{f}" for f in BaseSQLModel.se_fields])
    _su_aggfields_sql = BaseSQLModel.su_aggfields_sql

    sql = f"""
        WITH bleachingqc_su AS (
            {BleachingQCSUSQLModel.sql}
        )
        SELECT sample_event_id AS id,
        {_se_fields},
        data_policy_bleachingqc,
        {_su_aggfields_sql},
        COUNT(pseudosu_id) AS sample_unit_count,
        ROUND(AVG(quadrat_size), 1) AS quadrat_size_avg,
        ROUND(AVG(count_total), 1) AS count_total_avg,
        ROUND(AVG(count_genera), 1) AS count_genera_avg,
        ROUND(AVG(percent_normal), 1) AS percent_normal_avg,
        ROUND(AVG(percent_pale), 1) AS percent_pale_avg,
        ROUND(AVG(percent_bleached), 1) AS percent_bleached_avg,
        ROUND(AVG(quadrat_count), 1) AS quadrat_count_avg,
        ROUND(AVG(percent_hard_avg), 1) AS percent_hard_avg_avg,
        ROUND(AVG(percent_soft_avg), 1) AS percent_soft_avg_avg,
        ROUND(AVG(percent_algae_avg), 1) AS percent_algae_avg_avg

        FROM bleachingqc_su
        GROUP BY
        {_se_fields},
        data_policy_bleachingqc
    """

    sql_args = dict(project_id=SQLTableArg(required=True))

    objects = SQLTableManager()

    sample_unit_count = models.PositiveSmallIntegerField()
    depth_avg = models.DecimalField(
        max_digits=4, decimal_places=2, verbose_name=_("depth (m)")
    )
    current_name = models.CharField(max_length=100)
    tide_name = models.CharField(max_length=100)
    visibility_name = models.CharField(max_length=100)
    quadrat_size_avg = models.DecimalField(decimal_places=2, max_digits=6)
    count_total_avg = models.DecimalField(max_digits=5, decimal_places=1)
    count_genera_avg = models.DecimalField(max_digits=4, decimal_places=1)
    percent_normal_avg = models.DecimalField(max_digits=4, decimal_places=1)
    percent_pale_avg = models.DecimalField(max_digits=4, decimal_places=1)
    percent_bleached_avg = models.DecimalField(max_digits=4, decimal_places=1)
    quadrat_count_avg = models.DecimalField(max_digits=4, decimal_places=1)
    percent_hard_avg_avg = models.DecimalField(max_digits=4, decimal_places=1)
    percent_soft_avg_avg = models.DecimalField(max_digits=4, decimal_places=1)
    percent_algae_avg_avg = models.DecimalField(max_digits=4, decimal_places=1)
    data_policy_bleachingqc = models.CharField(max_length=50)

    class Meta:
        db_table = "bleachingqc_se_sm"
        managed = False
