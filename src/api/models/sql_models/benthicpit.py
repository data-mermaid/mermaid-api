from django.contrib.gis.db import models
from django.contrib.postgres.fields import JSONField
from django.utils.translation import ugettext_lazy as _

from sqltables import SQLTableArg, SQLTableManager
from .base import BaseSQLModel, BaseSUSQLModel, sample_event_sql_template


class BenthicPITObsSQLModel(BaseSUSQLModel):
    _se_fields = ", ".join([f"se.{f}" for f in BaseSUSQLModel.se_fields])
    _su_fields = BaseSUSQLModel.su_fields_sql
    sql = f"""
        WITH se AS (
            {sample_event_sql_template}
        )
        SELECT o.id, pseudosu_id,
            {_se_fields},
            {_su_fields},
            se.data_policy_benthicpit,
            su.number AS transect_number,
            su.len_surveyed AS transect_len_surveyed,
            rs.name AS reef_slope,
            tt.interval_size,
            tt.interval_start,
            o."interval",
            cat.name AS benthic_category,
            b.name AS benthic_attribute,
            gf.name AS growth_form,
            o.notes AS observation_notes
        FROM obs_benthicpit o
            JOIN ( WITH RECURSIVE tree(child, root) AS (
                        SELECT c_1.id,
                            c_1.id
                        FROM benthic_attribute c_1
                            LEFT JOIN benthic_attribute p ON c_1.parent_id = p.id
                        WHERE p.id IS NULL
                        UNION
                        SELECT benthic_attribute.id,
                            tree_1.root
                        FROM tree tree_1
                            JOIN benthic_attribute ON tree_1.child = benthic_attribute.parent_id
                        )
                SELECT tree.child,
                    tree.root
                FROM tree) category ON o.attribute_id = category.child
            JOIN benthic_attribute cat ON category.root = cat.id
            JOIN benthic_attribute b ON o.attribute_id = b.id
            LEFT JOIN growth_form gf ON o.growth_form_id = gf.id
            JOIN transectmethod_benthicpit tt ON o.benthicpit_id = tt.transectmethod_ptr_id
            JOIN transect_benthic su ON tt.transect_id = su.id
            LEFT JOIN api_current c ON su.current_id = c.id
            LEFT JOIN api_tide t ON su.tide_id = t.id
            LEFT JOIN api_visibility v ON su.visibility_id = v.id
            LEFT JOIN api_relativedepth r ON su.relative_depth_id = r.id
            LEFT JOIN api_reefslope rs ON su.reef_slope_id = rs.id
            JOIN (
                SELECT
                    tt_1.transect_id,
                    jsonb_agg(jsonb_build_object(
                        'id', p.id, 
                        'name', (COALESCE(p.first_name, '' :: character varying) :: text || ' ' :: text) || 
                            COALESCE(p.last_name, '' :: character varying) :: text
                    )) AS observers
                FROM
                    observer o1
                    JOIN profile p ON o1.profile_id = p.id
                    JOIN transectmethod tm ON o1.transectmethod_id = tm.id
                    JOIN transectmethod_benthicpit tt_1 ON tm.id = tt_1.transectmethod_ptr_id
                    JOIN transect_benthic as tb ON tb.id = tt_1.transect_id
                    JOIN se ON se.sample_event_id = tb.sample_event_id
                GROUP BY
                    tt_1.transect_id
            ) observers ON su.id = observers.transect_id
            JOIN se ON su.sample_event_id = se.sample_event_id
            INNER JOIN (
                SELECT 
                    pseudosu_id,
                    UNNEST(sample_unit_ids) AS sample_unit_id
                FROM (
                    SELECT 
                        uuid_generate_v4() AS pseudosu_id,
                        array_agg(DISTINCT su.id) AS sample_unit_ids
                    FROM transect_benthic su
                    JOIN se ON se.sample_event_id = su.sample_event_id
                    GROUP BY {", ".join(BaseSUSQLModel.transect_su_fields)}
                ) pseudosu
            ) pseudosu_su ON (su.id = pseudosu_su.sample_unit_id)
    """

    sql_args = dict(project_id=SQLTableArg(required=True))

    objects = SQLTableManager()

    sample_unit_id = models.UUIDField()
    transect_number = models.PositiveSmallIntegerField()
    transect_len_surveyed = models.PositiveSmallIntegerField(
        verbose_name=_("transect length surveyed (m)")
    )
    reef_slope = models.CharField(max_length=50)
    interval_size = models.DecimalField(
        max_digits=4, decimal_places=2, default=0.5, verbose_name=_("interval size (m)")
    )
    interval_start = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0.5,
        verbose_name=_("interval start (m)"),
    )
    interval = models.DecimalField(max_digits=7, decimal_places=2)
    benthic_category = models.CharField(max_length=100)
    benthic_attribute = models.CharField(max_length=100)
    growth_form = models.CharField(max_length=100)
    observation_notes = models.TextField(blank=True)
    data_policy_benthicpit = models.CharField(max_length=50)

    class Meta:
        db_table = "benthicpit_obs_sm"
        managed = False


class BenthicPITSUSQLModel(BaseSUSQLModel):
    # Unique combination of these fields defines a single (pseudo) sample unit. All other fields are aggregated.
    su_fields = BaseSUSQLModel.se_fields + [
        "depth",
        "transect_number",
        "transect_len_surveyed",
        "interval_size",
        "interval_start",
        "data_policy_benthicpit",
    ]

    _su_fields = ", ".join(su_fields)
    _su_fields_qualified = ", ".join([f"benthicpit_obs.{f}" for f in su_fields])
    _agg_su_fields = ", ".join(BaseSUSQLModel.agg_su_fields)
    _su_aggfields_sql = BaseSUSQLModel.su_aggfields_sql

    sql = f"""
        WITH benthicpit_obs AS (
            {BenthicPITObsSQLModel.sql}
        )
        SELECT NULL AS id,
        benthicpit_su.pseudosu_id,
        {_su_fields},
        benthicpit_su.{_agg_su_fields},
        reef_slope,
        percent_cover_by_benthic_category
        FROM (
            SELECT pseudosu_id,
            jsonb_agg(DISTINCT sample_unit_id) AS sample_unit_ids,
            {_su_fields_qualified},
            {_su_aggfields_sql},
            string_agg(DISTINCT reef_slope::text, ', '::text ORDER BY (reef_slope::text)) AS reef_slope

            FROM benthicpit_obs
            GROUP BY pseudosu_id,
            {_su_fields_qualified}
        ) benthicpit_su

        INNER JOIN (
            WITH cps AS (
                WITH cps_obs AS (
                    SELECT pseudosu_id,
                    benthic_category,
                    SUM(interval_size) AS category_length
                    FROM benthicpit_obs
                    GROUP BY pseudosu_id, benthic_category
                )
                SELECT cps_expanded.pseudosu_id, cps_expanded.benthic_category,
                COALESCE(cps_obs.category_length, 0) AS category_length
                FROM (
                    SELECT DISTINCT cps_obs.pseudosu_id, top_categories.benthic_category
                    FROM cps_obs
                    CROSS JOIN (
                        SELECT name AS benthic_category
                        FROM benthic_attribute
                        WHERE benthic_attribute.parent_id IS NULL
                    ) top_categories
                ) cps_expanded
                LEFT JOIN cps_obs ON (
                    cps_expanded.pseudosu_id = cps_obs.pseudosu_id AND 
                    cps_expanded.benthic_category = cps_obs.benthic_category
                )
            )
            SELECT cps.pseudosu_id,
            jsonb_object_agg(
                cps.benthic_category,
                ROUND(100 * cps.category_length / cat_totals.su_length, 2)
            ) AS percent_cover_by_benthic_category
            FROM cps
            INNER JOIN (
                SELECT pseudosu_id,
                SUM(category_length) AS su_length
                FROM cps
                GROUP BY pseudosu_id
            ) cat_totals ON (cps.pseudosu_id = cat_totals.pseudosu_id)
            GROUP BY cps.pseudosu_id
        ) cat_percents
        ON (benthicpit_su.pseudosu_id = cat_percents.pseudosu_id)

        INNER JOIN (
            SELECT pseudosu_id,
            jsonb_agg(DISTINCT observer) AS observers

            FROM (
                SELECT pseudosu_id,
                jsonb_array_elements(observers) AS observer
                FROM benthicpit_obs
                GROUP BY pseudosu_id, observers
            ) benthicpit_obs_obs
            GROUP BY pseudosu_id
        ) benthicpit_observers
        ON (benthicpit_su.pseudosu_id = benthicpit_observers.pseudosu_id)
    """

    sql_args = dict(project_id=SQLTableArg(required=True))

    objects = SQLTableManager()

    sample_unit_ids = JSONField()
    transect_number = models.PositiveSmallIntegerField()
    transect_len_surveyed = models.PositiveSmallIntegerField(
        verbose_name=_("transect length surveyed (m)")
    )
    reef_slope = models.CharField(max_length=50)
    interval_size = models.DecimalField(
        max_digits=4, decimal_places=2, default=0.5, verbose_name=_("interval size (m)")
    )
    interval_start = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0.5,
        verbose_name=_("interval start (m)"),
    )
    percent_cover_by_benthic_category = JSONField(null=True, blank=True)
    data_policy_benthicpit = models.CharField(max_length=50)

    class Meta:
        db_table = "benthicpit_su_sm"
        managed = False


class BenthicPITSESQLModel(BaseSQLModel):
    _se_fields = ", ".join([f"benthicpit_su.{f}" for f in BaseSQLModel.se_fields])
    _su_aggfields_sql = BaseSQLModel.su_aggfields_sql

    sql = f"""
        WITH benthicpit_su AS (
            {BenthicPITSUSQLModel.sql}
        )
        SELECT benthicpit_su.sample_event_id AS id,
        {_se_fields},
        data_policy_benthicpit,
        {_su_aggfields_sql},
        COUNT(benthicpit_su.pseudosu_id) AS sample_unit_count,
        percent_cover_by_benthic_category_avg

        FROM benthicpit_su

        INNER JOIN (
            SELECT sample_event_id,
            jsonb_object_agg(cat, ROUND(cat_percent::numeric, 2)) AS percent_cover_by_benthic_category_avg
            FROM (
                SELECT sample_event_id,
                cpdata.key AS cat,
                AVG(cpdata.value::float) AS cat_percent
                FROM benthicpit_su,
                jsonb_each_text(percent_cover_by_benthic_category) AS cpdata
                GROUP BY sample_event_id, cpdata.key
            ) AS benthicpit_su_cp
            GROUP BY sample_event_id
        ) AS benthicpit_se_cat_percents
        ON benthicpit_su.sample_event_id = benthicpit_se_cat_percents.sample_event_id

        GROUP BY
        {_se_fields},
        data_policy_benthicpit,
        percent_cover_by_benthic_category_avg
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
    percent_cover_by_benthic_category_avg = JSONField(null=True, blank=True)
    data_policy_benthicpit = models.CharField(max_length=50)

    class Meta:
        db_table = "benthicpit_se_sm"
        managed = False
