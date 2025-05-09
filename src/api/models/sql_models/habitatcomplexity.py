from django.contrib.gis.db import models
from django.utils.translation import gettext_lazy as _

from sqltables import SQLTableArg, SQLTableManager
from .base import BaseSQLModel, BaseSUSQLModel, project_where, sample_event_sql_template


class HabitatComplexityObsSQLModel(BaseSUSQLModel):
    _se_fields = ", ".join([f"se.{f}" for f in BaseSUSQLModel.se_fields])
    _su_fields = BaseSUSQLModel.su_fields_sql
    sql = f"""
        WITH se AS (
            {sample_event_sql_template}
        ),
        pseudosu_su AS MATERIALIZED (
            SELECT 
                pseudosu_id,
                UNNEST(sample_unit_ids) AS sample_unit_id
            FROM (
                SELECT 
                    uuid_generate_v4() AS pseudosu_id,
                    array_agg(DISTINCT su.id) AS sample_unit_ids
                FROM transect_benthic su
                JOIN se ON su.sample_event_id = se.sample_event_id
                GROUP BY {", ".join(BaseSUSQLModel.transect_su_fields)}
            ) pseudosu
        ) 
        SELECT o.id, pseudosu_id,
        {_se_fields},
        {_su_fields},
        se.data_policy_habitatcomplexity,
        su.number AS transect_number,
        su.len_surveyed AS transect_len_surveyed,
        rs.name AS reef_slope,
        tt.interval_size,
        o."interval",
        s.val AS score,
        s.name AS score_name,
        o.notes AS observation_notes
        FROM
            obs_habitatcomplexity o
            JOIN transectmethod_habitatcomplexity tt ON o.habitatcomplexity_id = tt.transectmethod_ptr_id
            JOIN transect_benthic su ON tt.transect_id = su.id
            JOIN se ON su.sample_event_id = se.sample_event_id
            JOIN pseudosu_su ON (su.id = pseudosu_su.sample_unit_id)
            JOIN (
                SELECT tt_1.transect_id,
                    jsonb_agg(jsonb_build_object('id', p.id, 'name', (COALESCE(p.first_name, ''::character varying)::text ||
                    ' '::text) || COALESCE(p.last_name, ''::character varying)::text)) AS observers
                FROM observer o1
                    JOIN profile p ON o1.profile_id = p.id
                    JOIN transectmethod tm ON o1.transectmethod_id = tm.id
                    JOIN transectmethod_habitatcomplexity tt_1 ON tm.id = tt_1.transectmethod_ptr_id
                    JOIN transect_benthic as tb ON tt_1.transect_id = tb.id
                    JOIN se ON tb.sample_event_id = se.sample_event_id
                GROUP BY tt_1.transect_id
            ) observers ON su.id = observers.transect_id
            JOIN api_habitatcomplexityscore s ON (o.score_id = s.id)
            LEFT JOIN api_current c ON su.current_id = c.id
            LEFT JOIN api_tide t ON su.tide_id = t.id
            LEFT JOIN api_visibility v ON su.visibility_id = v.id
            LEFT JOIN api_relativedepth r ON su.relative_depth_id = r.id
            LEFT JOIN api_reefslope rs ON su.reef_slope_id = rs.id     
    """

    sql_args = dict(
        project_id=SQLTableArg(sql=project_where, required=True),
    )

    objects = SQLTableManager()

    sample_unit_id = models.UUIDField()
    label = models.CharField(max_length=50, blank=True)
    relative_depth = models.CharField(max_length=50, null=True, blank=True)
    sample_time = models.TimeField(null=True, blank=True)
    observers = models.JSONField(null=True, blank=True)
    current_name = models.CharField(max_length=50, null=True, blank=True)
    tide_name = models.CharField(max_length=50, null=True, blank=True)
    visibility_name = models.CharField(max_length=50, null=True, blank=True)
    sample_unit_notes = models.TextField(blank=True)

    sample_time = models.TimeField()
    transect_number = models.PositiveSmallIntegerField()
    transect_len_surveyed = models.PositiveSmallIntegerField(
        verbose_name=_("transect length surveyed (m)")
    )
    reef_slope = models.CharField(max_length=50)
    interval_size = models.DecimalField(
        max_digits=4, decimal_places=2, default=0.5, verbose_name=_("interval size (m)")
    )
    interval = models.DecimalField(max_digits=7, decimal_places=2)
    observation_notes = models.TextField(blank=True)
    score = models.PositiveSmallIntegerField()
    score_name = models.CharField(max_length=100)
    data_policy_habitatcomplexity = models.CharField(max_length=50)
    pseudosu_id = models.UUIDField()

    class Meta:
        db_table = "habitatcomplexity_obs_sm"
        managed = False


class HabitatComplexitySUSQLModel(BaseSUSQLModel):
    # Unique combination of these fields defines a single (pseudo) sample unit. All other fields are aggregated.
    su_fields = BaseSUSQLModel.se_fields + [
        "depth",
        "transect_number",
        "transect_len_surveyed",
        "interval_size",
        "data_policy_habitatcomplexity",
    ]

    _su_fields = ", ".join(su_fields)
    _su_fields_qualified = ", ".join([f"habitatcomplexity_obs.{f}" for f in su_fields])
    _su_aggfields_sql = BaseSUSQLModel.su_aggfields_sql
    _agg_su_fields = ", ".join(BaseSUSQLModel.agg_su_fields)

    sql = f"""
        WITH habitatcomplexity_obs AS (
            {HabitatComplexityObsSQLModel.sql}
        ),
        habcomp_observers AS (
            SELECT pseudosu_id,
            jsonb_agg(DISTINCT observer) AS observers

            FROM (
                SELECT pseudosu_id,
                jsonb_array_elements(observers) AS observer
                FROM habitatcomplexity_obs
                GROUP BY pseudosu_id, observers
            ) habcomp_obs_obs
            GROUP BY pseudosu_id
        )
        SELECT uuid_generate_v4() AS id,
        habcomp_su.pseudosu_id,
        {_su_fields},
        habcomp_su.{_agg_su_fields},
        reef_slope,
        score_avg,
        score_sd,
        observation_count
        FROM (
            SELECT pseudosu_id,
            jsonb_agg(DISTINCT sample_unit_id) AS sample_unit_ids,
            {_su_fields_qualified},
            {_su_aggfields_sql},
            string_agg(DISTINCT reef_slope::text, ', '::text ORDER BY (reef_slope::text)) AS reef_slope,
            ROUND(AVG(score), 2) AS score_avg,
            ROUND(STDDEV(score), 2) AS score_sd,
            COUNT(habitatcomplexity_obs.id) AS observation_count

            FROM habitatcomplexity_obs
            GROUP BY pseudosu_id,
            {_su_fields_qualified}
        ) habcomp_su

        INNER JOIN habcomp_observers
        ON (habcomp_su.pseudosu_id = habcomp_observers.pseudosu_id)
    """

    sql_args = dict(
        project_id=SQLTableArg(sql=project_where, required=True),
    )

    objects = SQLTableManager()

    sample_unit_ids = models.JSONField()
    label = models.TextField(blank=True)
    relative_depth = models.TextField(blank=True)
    sample_time = models.TextField(blank=True)
    observers = models.JSONField(null=True, blank=True)
    current_name = models.TextField(blank=True)
    tide_name = models.TextField(blank=True)
    visibility_name = models.TextField(blank=True)
    sample_unit_notes = models.TextField(blank=True)

    transect_number = models.PositiveSmallIntegerField()
    transect_len_surveyed = models.PositiveSmallIntegerField(
        verbose_name=_("transect length surveyed (m)")
    )
    reef_slope = models.CharField(max_length=50)
    score_avg = models.DecimalField(decimal_places=2, max_digits=3)
    score_sd = models.DecimalField(decimal_places=2, max_digits=3, null=True, blank=True)
    observation_count = models.PositiveSmallIntegerField()
    data_policy_habitatcomplexity = models.CharField(max_length=50)
    pseudosu_id = models.UUIDField()

    class Meta:
        db_table = "habitatcomplexity_su_sm"
        managed = False


class HabitatComplexitySESQLModel(BaseSQLModel):
    _se_fields = ", ".join([f"habitatcomplexity_su.{f}" for f in BaseSQLModel.se_fields])
    _su_aggfields_sql = BaseSQLModel.su_aggfields_sql
    sql = f"""
        WITH habitatcomplexity_su AS (
            {HabitatComplexitySUSQLModel.sql}
        ),
        se_observers AS (
            SELECT sample_event_id,
            jsonb_agg(DISTINCT observer ORDER BY observer) AS observers
            FROM (
                SELECT sample_event_id, jsonb_array_elements(observers) AS observer
                FROM habitatcomplexity_su
            ) AS su_observers
            GROUP BY sample_event_id
        )
        SELECT habitatcomplexity_su.sample_event_id AS id,
        {_se_fields},
        data_policy_habitatcomplexity,
        se_observers.observers,
        {_su_aggfields_sql},
        COUNT(pseudosu_id) AS sample_unit_count,
        ROUND(AVG(score_avg), 2) AS score_avg_avg,
        ROUND(STDDEV(score_avg), 2) AS score_avg_sd,
        ROUND(AVG(observation_count), 2) AS observation_count_avg,
        ROUND(STDDEV(observation_count), 2) AS observation_count_sd
        
        FROM habitatcomplexity_su
        INNER JOIN se_observers ON (habitatcomplexity_su.sample_event_id = se_observers.sample_event_id)
        GROUP BY
        {_se_fields},
        data_policy_habitatcomplexity,
        se_observers.observers
    """

    sql_args = dict(
        project_id=SQLTableArg(sql=project_where, required=True),
    )

    objects = SQLTableManager()

    sample_unit_count = models.PositiveSmallIntegerField()
    depth_avg = models.DecimalField(
        max_digits=4, decimal_places=2, verbose_name=_("depth mean (m)")
    )
    depth_sd = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        verbose_name=_("depth standard deviation (m)"),
        blank=True,
        null=True,
    )
    observers = models.JSONField(null=True, blank=True)
    current_name = models.CharField(max_length=100)
    tide_name = models.CharField(max_length=100)
    visibility_name = models.CharField(max_length=100)
    score_avg_avg = models.DecimalField(decimal_places=2, max_digits=3)
    score_avg_sd = models.DecimalField(decimal_places=2, max_digits=3, blank=True, null=True)
    observation_count_avg = models.DecimalField(decimal_places=2, max_digits=6)
    observation_count_sd = models.DecimalField(
        decimal_places=2, max_digits=6, blank=True, null=True
    )
    data_policy_habitatcomplexity = models.CharField(max_length=50)

    class Meta:
        db_table = "habitatcomplexity_su_se"
        managed = False
