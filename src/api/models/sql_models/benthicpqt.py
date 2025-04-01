from django.contrib.gis.db import models
from django.utils.translation import gettext_lazy as _

from sqltables import SQLTableArg, SQLTableManager
from .base import BaseSQLModel, BaseSUSQLModel, project_where, sample_event_sql_template


class BenthicPhotoQuadratTransectObsSQLModel(BaseSUSQLModel):
    _se_fields = ", ".join([f"se.{f}" for f in BaseSUSQLModel.se_fields])
    _su_fields = BaseSUSQLModel.su_fields_sql

    sql = f"""
        WITH benthicpqt_obs_cte AS MATERIALIZED (
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
                    FROM quadrat_transect su
                    JOIN se ON su.sample_event_id = se.sample_event_id
                    GROUP BY {", ".join(BaseSUSQLModel.transect_su_fields)}
                ) pseudosu
            ) 
            SELECT
                o.id, pseudosu_id,
                { _se_fields },
                { _su_fields },
                se.data_policy_benthicpqt,
                su.number AS transect_number,
                su.len_surveyed AS transect_len_surveyed,
                su.quadrat_size AS quadrat_size,
                su.num_quadrats AS num_quadrats,
                su.num_points_per_quadrat AS num_points_per_quadrat,
                rs.name AS reef_slope,
                o.quadrat_number,
                cat.name AS benthic_category,
                b.id AS attribute_id,
                b.name AS benthic_attribute,
                gf.id AS growth_form_id,
                gf.name AS growth_form,
                o.num_points,
                o.notes AS observation_notes
            FROM
                obs_benthic_photo_quadrat o
                JOIN transectmethod_benthicpqt tt ON o.benthic_photo_quadrat_transect_id = tt.transectmethod_ptr_id
                JOIN quadrat_transect su ON tt.quadrat_transect_id = su.id
                JOIN se ON su.sample_event_id = se.sample_event_id
                JOIN pseudosu_su ON (su.id = pseudosu_su.sample_unit_id)
                JOIN (
                    SELECT
                        tt_1.quadrat_transect_id,
                        jsonb_agg(jsonb_build_object(
                            'id', p.id,
                            'name', (COALESCE(p.first_name, '' :: character varying) :: text || ' ' :: text) ||
                                COALESCE(p.last_name, '' :: character varying) :: text
                        )) AS observers
                    FROM
                        observer o1
                        JOIN profile p ON o1.profile_id = p.id
                        JOIN transectmethod tm ON o1.transectmethod_id = tm.id
                        JOIN transectmethod_benthicpqt tt_1 ON tm.id = tt_1.transectmethod_ptr_id
                        JOIN quadrat_transect as su ON tt_1.quadrat_transect_id = su.id
                        JOIN se ON su.sample_event_id = se.sample_event_id
                    GROUP BY
                        tt_1.quadrat_transect_id
                ) observers ON su.id = observers.quadrat_transect_id
                JOIN (
                    WITH RECURSIVE tree(child, root) AS (
                        SELECT
                            c_1.id,
                            c_1.id
                        FROM
                            benthic_attribute c_1
                        LEFT JOIN benthic_attribute p ON c_1.parent_id = p.id
                        WHERE
                            p.id IS NULL
                        UNION
                        SELECT
                            benthic_attribute.id,
                            tree_1.root
                        FROM
                            tree tree_1
                            JOIN benthic_attribute ON tree_1.child = benthic_attribute.parent_id
                    )
                    SELECT
                        tree.child,
                        tree.root
                    FROM
                        tree
                ) category ON o.attribute_id = category.child
                JOIN benthic_attribute cat ON category.root = cat.id
                JOIN benthic_attribute b ON o.attribute_id = b.id
                LEFT JOIN growth_form gf ON o.growth_form_id = gf.id
                LEFT JOIN api_current c ON su.current_id = c.id
                LEFT JOIN api_tide t ON su.tide_id = t.id
                LEFT JOIN api_visibility v ON su.visibility_id = v.id
                LEFT JOIN api_relativedepth r ON su.relative_depth_id = r.id
                LEFT JOIN api_reefslope rs ON su.reef_slope_id = rs.id
        ),
        ba_lh_counts AS (
            SELECT 
                benthicattribute_id, 
                COUNT(*) AS cnt
            FROM benthic_attribute_life_histories
            GROUP BY benthicattribute_id
        ),
        gf_lh_counts AS (
            SELECT 
                attribute_id, 
                growth_form_id, 
                COUNT(*) AS cnt
            FROM ba_gf_life_histories
            GROUP BY attribute_id, growth_form_id
        )
        
        SELECT *,
        (
            WITH life_histories_data AS (
                SELECT
                    blh.id,
                    blh.name,
                        COALESCE(ROUND(1.0 / NULLIF(COALESCE(gf.cnt, ba.cnt), 0), 3), 0) AS proportion,
                        COALESCE(ROUND(1.0 / NULLIF(gf.cnt, 0), 3), 0) AS proportion_gf
                FROM benthic_lifehistory blh
                LEFT JOIN ba_gf_life_histories gf_lh ON gf_lh.life_history_id = blh.id
                    AND gf_lh.attribute_id = benthicpqt_obs_cte.attribute_id 
                    AND gf_lh.growth_form_id = benthicpqt_obs_cte.growth_form_id
                LEFT JOIN gf_lh_counts gf ON gf_lh.attribute_id = gf.attribute_id AND gf_lh.growth_form_id = gf.growth_form_id
                LEFT JOIN benthic_attribute_life_histories balh ON balh.benthiclifehistory_id = blh.id
                    AND balh.benthicattribute_id = benthicpqt_obs_cte.attribute_id
                LEFT JOIN ba_lh_counts ba ON balh.benthicattribute_id = ba.benthicattribute_id
            )
            SELECT jsonb_agg(jsonb_build_object(
                'id', lh.id,
                'name', lh.name,
                'proportion', 
                    CASE 
                        WHEN EXISTS (
                            SELECT 1 FROM life_histories_data lh_sub
                            WHERE lh_sub.proportion_gf > 0
                        )
                        THEN CASE WHEN lh.proportion_gf > 0 THEN lh.proportion ELSE 0 END
                        ELSE lh.proportion
                    END
            ) ORDER BY lh.name)
            FROM life_histories_data lh
        ) AS life_histories
        FROM benthicpqt_obs_cte
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

    transect_number = models.PositiveSmallIntegerField()
    transect_len_surveyed = models.PositiveSmallIntegerField(
        verbose_name=_("transect length surveyed (m)")
    )
    quadrat_size = models.DecimalField(decimal_places=2, max_digits=6)
    num_quadrats = models.PositiveSmallIntegerField()
    num_points_per_quadrat = models.PositiveSmallIntegerField()
    reef_slope = models.CharField(max_length=50)
    quadrat_number = models.PositiveSmallIntegerField(verbose_name="quadrat number")
    benthic_category = models.CharField(max_length=100)
    benthic_attribute = models.CharField(max_length=100)
    growth_form = models.CharField(max_length=100)
    num_points = models.PositiveSmallIntegerField()
    life_histories = models.JSONField(null=True, blank=True)
    observation_notes = models.TextField(blank=True)
    data_policy_benthicpqt = models.CharField(max_length=50)
    pseudosu_id = models.UUIDField()

    class Meta:
        db_table = "benthicpqt_obs_sm"
        managed = False


class BenthicPhotoQuadratTransectSUSQLModel(BaseSUSQLModel):
    # Unique combination of these fields defines a single (pseudo) sample unit. All other fields are aggregated.
    su_fields = BaseSUSQLModel.se_fields + [
        "depth",
        "transect_number",
        "transect_len_surveyed",
        "data_policy_benthicpqt",
    ]

    _su_fields = ", ".join(su_fields)
    _su_fields_qualified = ", ".join([f"benthicpqt_obs.{f}" for f in su_fields])
    _agg_su_fields = ", ".join(BaseSUSQLModel.agg_su_fields)
    _su_aggfields_sql = BaseSUSQLModel.su_aggfields_sql

    sql = f"""
        WITH benthicpqt_obs AS (
            SELECT * FROM ({BenthicPhotoQuadratTransectObsSQLModel.sql}) AS benthicpqt_obs_core WHERE project_id = '%(project_id)s'::uuid
            AND benthic_category != 'Other'
        ),
        benthicpqt_observers AS (
            SELECT pseudosu_id,
            jsonb_agg(DISTINCT observer) AS observers

            FROM (
                SELECT pseudosu_id,
                jsonb_array_elements(observers) AS observer
                FROM benthicpqt_obs
                GROUP BY pseudosu_id, observers
            ) benthicpqt_obs_obs
            GROUP BY pseudosu_id
        ),
        cat_percents AS (
            WITH cps AS (
                WITH cps_obs AS (
                    SELECT pseudosu_id,
                    benthic_category,
                    SUM(num_points) AS category_num_points
                    FROM benthicpqt_obs
                    GROUP BY pseudosu_id, benthic_category
                )
                SELECT cps_expanded.pseudosu_id, cps_expanded.benthic_category,
                COALESCE(cps_obs.category_num_points, 0) AS category_num_points
                FROM (
                    SELECT DISTINCT cps_obs.pseudosu_id, top_categories.benthic_category
                    FROM cps_obs
                    CROSS JOIN (
                        SELECT name AS benthic_category
                        FROM benthic_attribute
                        WHERE benthic_attribute.parent_id IS NULL
                        AND benthic_attribute.name != 'Other'
                    ) top_categories
                ) cps_expanded
                LEFT JOIN cps_obs ON (
                    cps_expanded.pseudosu_id = cps_obs.pseudosu_id AND
                    cps_expanded.benthic_category = cps_obs.benthic_category
                )
            )
            SELECT
                cps.pseudosu_id,
                jsonb_object_agg(
                    cps.benthic_category,
                    ROUND(100 * cps.category_num_points / cat_totals.su_num_points, 2)
                ) AS percent_cover_benthic_category
            FROM cps
            INNER JOIN (
                SELECT pseudosu_id,
                SUM(category_num_points) AS su_num_points
                FROM cps
                GROUP BY pseudosu_id
            ) cat_totals ON (cps.pseudosu_id = cat_totals.pseudosu_id)
            GROUP BY cps.pseudosu_id
        ),
        life_histories_agg AS (
            SELECT lh.pseudosu_id,
            jsonb_object_agg(
                lh.name,
                CASE WHEN su_points.total_points > 0 THEN ROUND(100 * lh.proportion_sum / su_points.total_points, 2) ELSE 0 END
            ) AS percent_cover_life_histories
            FROM (
                SELECT pseudosu_id,
                       life_history->>'id' AS id,
                       life_history->>'name' AS name,
                       SUM(COALESCE((life_history->>'proportion')::numeric, 0) * benthicpqt_obs.num_points) AS proportion_sum
                FROM benthicpqt_obs
                CROSS JOIN jsonb_array_elements(life_histories) AS life_history
                GROUP BY pseudosu_id, life_history->>'id', life_history->>'name'
            ) lh
            INNER JOIN (
                SELECT pseudosu_id, 
                SUM(num_points) AS total_points
                FROM benthicpqt_obs
                GROUP BY pseudosu_id
            ) su_points
            ON lh.pseudosu_id = su_points.pseudosu_id
            GROUP BY lh.pseudosu_id
        )        
        SELECT uuid_generate_v4() AS id,
        benthicpqt_su.pseudosu_id,
        {_su_fields},
        benthicpqt_su.{_agg_su_fields},
        num_points_nonother,
        reef_slope,
        percent_cover_benthic_category,
        percent_cover_life_histories
        FROM (
            SELECT pseudosu_id,
            jsonb_agg(DISTINCT sample_unit_id) AS sample_unit_ids,
            {_su_fields_qualified},
            {_su_aggfields_sql},
            SUM(num_points) AS num_points_nonother,
            string_agg(DISTINCT reef_slope::text, ', '::text ORDER BY (reef_slope::text)) AS reef_slope
            FROM benthicpqt_obs
            GROUP BY pseudosu_id,
            {_su_fields_qualified}
        ) benthicpqt_su

        INNER JOIN  cat_percents
        ON (benthicpqt_su.pseudosu_id = cat_percents.pseudosu_id)
        INNER JOIN life_histories_agg
        ON (benthicpqt_su.pseudosu_id = life_histories_agg.pseudosu_id)
        INNER JOIN benthicpqt_observers
        ON (benthicpqt_su.pseudosu_id = benthicpqt_observers.pseudosu_id)
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
    num_points_nonother = models.PositiveSmallIntegerField(
        verbose_name="number of non-'Other' points for all observations in all quadrats for the transect"
    )
    reef_slope = models.CharField(max_length=50)
    percent_cover_benthic_category = models.JSONField(null=True, blank=True)
    percent_cover_life_histories = models.JSONField(null=True, blank=True)
    data_policy_benthicpqt = models.CharField(max_length=50)
    pseudosu_id = models.UUIDField()

    class Meta:
        db_table = "benthicpqt_su_sm"
        managed = False


class BenthicPhotoQuadratTransectSESQLModel(BaseSQLModel):
    _se_fields = ", ".join([f"benthicpqt_su.{f}" for f in BaseSQLModel.se_fields])
    _su_aggfields_sql = BaseSQLModel.su_aggfields_sql

    sql = f"""
        WITH benthicpqt_su AS (
            {BenthicPhotoQuadratTransectSUSQLModel.sql}
        ),
        se_observers AS (
            SELECT sample_event_id,
            jsonb_agg(DISTINCT observer ORDER BY observer) AS observers
            FROM (
                SELECT sample_event_id, jsonb_array_elements(observers) AS observer
                FROM benthicpqt_su
            ) AS su_observers
            GROUP BY sample_event_id
        )
        SELECT benthicpqt_su.sample_event_id AS id,
        {_se_fields},
        data_policy_benthicpqt,
        se_observers.observers,
        {_su_aggfields_sql},
        COUNT(benthicpqt_su.pseudosu_id) AS sample_unit_count,
        SUM(benthicpqt_su.num_points_nonother) AS num_points_nonother,
        percent_cover_benthic_category_avg,
        percent_cover_benthic_category_sd,
        percent_cover_life_histories_avg,
        percent_cover_life_histories_sd
        FROM benthicpqt_su

        INNER JOIN (
            SELECT sample_event_id,
            jsonb_object_agg(cat, ROUND(cat_percent_avg :: numeric, 2)) AS percent_cover_benthic_category_avg,
            jsonb_object_agg(cat, ROUND(cat_percent_sd :: numeric, 2)) AS percent_cover_benthic_category_sd
            FROM (
                SELECT sample_event_id,
                cpdata.key AS cat,
                AVG(cpdata.value :: float) AS cat_percent_avg,
                STDDEV(cpdata.value :: float) AS cat_percent_sd
                FROM benthicpqt_su,
                jsonb_each_text(percent_cover_benthic_category) AS cpdata
                GROUP BY sample_event_id, cpdata.key
            ) AS benthicpqt_su_cp
            GROUP BY sample_event_id
        ) AS benthicpqt_se_cat_percents
        ON benthicpqt_su.sample_event_id = benthicpqt_se_cat_percents.sample_event_id
        INNER JOIN (
            SELECT sample_event_id,
            jsonb_object_agg(benthicpqt_su_lh.name, ROUND(proportion_avg :: numeric, 2)) AS percent_cover_life_histories_avg,
            jsonb_object_agg(benthicpqt_su_lh.name, ROUND(proportion_sd :: numeric, 2)) AS percent_cover_life_histories_sd
            FROM (
                SELECT sample_event_id,
                life_history.key AS name,
                AVG(life_history.value :: float) AS proportion_avg,
                STDDEV(life_history.value :: float) AS proportion_sd
                FROM benthicpqt_su, 
                jsonb_each_text(percent_cover_life_histories) AS life_history
                GROUP BY sample_event_id, life_history.key
            ) AS benthicpqt_su_lh
            GROUP BY sample_event_id
        ) AS benthicpqt_se_lhs
        ON benthicpqt_su.sample_event_id = benthicpqt_se_lhs.sample_event_id
        INNER JOIN se_observers ON (benthicpqt_su.sample_event_id = se_observers.sample_event_id)

        GROUP BY
        {_se_fields},
        data_policy_benthicpqt,
        percent_cover_benthic_category_avg,
        percent_cover_benthic_category_sd,
        percent_cover_life_histories_avg,
        percent_cover_life_histories_sd,
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
    num_points_nonother = models.PositiveSmallIntegerField(
        verbose_name="number of non-'Other' points for all observations in all transects for the sample event"
    )
    percent_cover_benthic_category_avg = models.JSONField(null=True, blank=True)
    percent_cover_benthic_category_sd = models.JSONField(null=True, blank=True)
    percent_cover_life_histories_avg = models.JSONField(null=True, blank=True)
    percent_cover_life_histories_sd = models.JSONField(null=True, blank=True)
    data_policy_benthicpqt = models.CharField(max_length=50)

    class Meta:
        db_table = "benthicpqt_se_sm"
        managed = False
