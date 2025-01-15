from django.contrib.gis.db import models
from django.utils.translation import gettext_lazy as _

from sqltables import SQLTableArg, SQLTableManager
from .base import BaseSQLModel, BaseSUSQLModel, project_where, sample_event_sql_template


class BleachingQCColoniesBleachedObsSQLModel(BaseSUSQLModel):
    _se_fields = ", ".join([f"se.{f}" for f in BaseSUSQLModel.se_fields])
    _su_fields = BaseSUSQLModel.su_fields_sql

    sql = f"""
    WITH obs_colonies_bleached_cte AS MATERIALIZED (
        WITH se AS (
            {sample_event_sql_template}
        )
        SELECT o.id,
            { _se_fields },
            { _su_fields },
            se.data_policy_bleachingqc,
            su.quadrat_size,
            cat.name AS benthic_category,
            b.id AS attribute_id,
            b.name AS benthic_attribute,
            gf.id AS growth_form_id,
            gf.name AS growth_form,
            o.count_normal,
            o.count_pale,
            o.count_20,
            o.count_50,
            o.count_80,
            o.count_100,
            o.count_dead,
            o.notes AS observation_notes
        FROM
            obs_colonies_bleached o
            JOIN transectmethod_bleaching_quadrat_collection tt ON o.bleachingquadratcollection_id = tt.transectmethod_ptr_id
            JOIN quadrat_collection su ON tt.quadrat_id = su.id
            JOIN se ON su.sample_event_id = se.sample_event_id
            JOIN (
                SELECT
                    tt_1.quadrat_id,
                    jsonb_agg(jsonb_build_object(
                        'id', p.id, 
                        'name', (COALESCE(p.first_name, '' :: character varying) :: text || ' ' :: text) || 
                            COALESCE(p.last_name, '' :: character varying) :: text
                    )) AS observers
                FROM
                    observer o1
                    JOIN profile p ON o1.profile_id = p.id
                    JOIN transectmethod tm ON o1.transectmethod_id = tm.id
                    JOIN transectmethod_bleaching_quadrat_collection tt_1 ON tm.id = tt_1.transectmethod_ptr_id
                    JOIN quadrat_collection as qc ON tt_1.quadrat_id = qc.id
                    JOIN se ON qc.sample_event_id = se.sample_event_id
                GROUP BY
                    tt_1.quadrat_id
            ) observers ON su.id = observers.quadrat_id
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
            LEFT JOIN api_current c ON su.current_id = c.id
            LEFT JOIN api_tide t ON su.tide_id = t.id
            LEFT JOIN api_visibility v ON su.visibility_id = v.id
            LEFT JOIN api_relativedepth r ON su.relative_depth_id = r.id
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
                AND gf_lh.attribute_id = obs_colonies_bleached_cte.attribute_id 
                AND gf_lh.growth_form_id = obs_colonies_bleached_cte.growth_form_id
            LEFT JOIN gf_lh_counts gf ON gf_lh.attribute_id = gf.attribute_id AND gf_lh.growth_form_id = gf.growth_form_id
            LEFT JOIN benthic_attribute_life_histories balh ON balh.benthiclifehistory_id = blh.id
                AND balh.benthicattribute_id = obs_colonies_bleached_cte.attribute_id
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
    FROM obs_colonies_bleached_cte
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

    quadrat_size = models.DecimalField(decimal_places=2, max_digits=6)
    benthic_category = models.CharField(max_length=100)
    benthic_attribute = models.CharField(max_length=100)
    growth_form = models.CharField(max_length=100)
    life_histories = models.JSONField(null=True, blank=True)
    count_normal = models.PositiveSmallIntegerField(verbose_name="normal", default=0)
    count_pale = models.PositiveSmallIntegerField(verbose_name="pale", default=0)
    count_20 = models.PositiveSmallIntegerField(verbose_name="0-20% bleached", default=0)
    count_50 = models.PositiveSmallIntegerField(verbose_name="20-50% bleached", default=0)
    count_80 = models.PositiveSmallIntegerField(verbose_name="50-80% bleached", default=0)
    count_100 = models.PositiveSmallIntegerField(verbose_name="80-100% bleached", default=0)
    count_dead = models.PositiveSmallIntegerField(verbose_name="recently dead", default=0)
    observation_notes = models.TextField(blank=True)
    data_policy_bleachingqc = models.CharField(max_length=50)

    class Meta:
        db_table = "bleachingqc_colonies_bleached_obs_sm"
        managed = False


class BleachingQCQuadratBenthicPercentObsSQLModel(BaseSUSQLModel):
    _se_fields = ", ".join([f"se.{f}" for f in BaseSUSQLModel.se_fields])
    _su_fields = BaseSUSQLModel.su_fields_sql

    sql = f"""
        WITH se AS (
            {sample_event_sql_template}
        ) 
        SELECT o.id,
        {_se_fields},
        {_su_fields},
        se.data_policy_bleachingqc,
        su.quadrat_size,
        o.quadrat_number,
        o.percent_hard,
        o.percent_soft,
        o.percent_algae,
        o.notes AS observation_notes
        FROM
        obs_quadrat_benthic_percent o
        JOIN transectmethod_bleaching_quadrat_collection tt ON o.bleachingquadratcollection_id = tt.transectmethod_ptr_id
        JOIN quadrat_collection su ON tt.quadrat_id = su.id
        LEFT JOIN api_current c ON su.current_id = c.id
        LEFT JOIN api_tide t ON su.tide_id = t.id
        LEFT JOIN api_visibility v ON su.visibility_id = v.id
        LEFT JOIN api_relativedepth r ON su.relative_depth_id = r.id
        JOIN (
            SELECT
                tt_1.quadrat_id,
                jsonb_agg(jsonb_build_object(
                    'id', p.id, 
                    'name', (COALESCE(p.first_name, '' :: character varying) :: text || ' ' :: text) || 
                        COALESCE(p.last_name, '' :: character varying) :: text
                )) AS observers
            FROM
                observer o1
                JOIN profile p ON o1.profile_id = p.id
                JOIN transectmethod tm ON o1.transectmethod_id = tm.id
                JOIN transectmethod_bleaching_quadrat_collection tt_1 ON tm.id = tt_1.transectmethod_ptr_id
                JOIN quadrat_collection as qc ON tt_1.quadrat_id = qc.id
                JOIN se ON qc.sample_event_id = se.sample_event_id
            GROUP BY
                tt_1.quadrat_id
        ) observers ON su.id = observers.quadrat_id
        JOIN se ON su.sample_event_id = se.sample_event_id
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

    quadrat_size = models.DecimalField(decimal_places=2, max_digits=6)
    quadrat_number = models.PositiveSmallIntegerField(verbose_name="quadrat number")
    percent_hard = models.PositiveSmallIntegerField(verbose_name="hard coral, % cover", default=0)
    percent_soft = models.PositiveSmallIntegerField(verbose_name="soft coral, % cover", default=0)
    percent_algae = models.PositiveSmallIntegerField(verbose_name="macroalgae, % cover", default=0)
    observation_notes = models.TextField(blank=True)
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
    _su_fields_qualified = ", ".join([f"bleachingqc_colonies_bleached_obs.{f}" for f in su_fields])
    _agg_su_fields = ", ".join(BaseSUSQLModel.agg_su_fields)
    _su_aggfields_sql = BaseSUSQLModel.su_aggfields_sql

    # SU fields and observers pieces both rely on being the same for both types of QC observations
    sql = f"""
        WITH bleachingqc_colonies_bleached_obs AS (
            SELECT * FROM ({BleachingQCColoniesBleachedObsSQLModel.sql}) AS bleachingqc_colonies_bleached_obs_core WHERE project_id = '%(project_id)s'::uuid          
            AND benthic_category != 'Other'
        ),
        bleachingqc_quadrat_benthic_percent_obs AS (
            {BleachingQCQuadratBenthicPercentObsSQLModel.sql}
        ),
        pseudosu_su AS (
            SELECT 
                pseudosu_id,
                UNNEST(sample_unit_ids) AS sample_unit_id
            FROM (
                SELECT 
                    uuid_generate_v4() AS pseudosu_id,
                    array_agg(DISTINCT su.id) AS sample_unit_ids
                FROM quadrat_collection su
                JOIN bleachingqc_colonies_bleached_obs bcbo ON su.sample_event_id = bcbo.sample_event_id
                GROUP BY {", ".join(BaseSUSQLModel.qc_su_fields)}
            ) pseudosu
        ),
        bleachingqc_observers AS (
            SELECT pseudosu_id,
            jsonb_agg(DISTINCT observer) AS observers

            FROM (
                SELECT pseudosu_id,
                jsonb_array_elements(observers) AS observer
                FROM bleachingqc_colonies_bleached_obs
                INNER JOIN pseudosu_su 
                ON(bleachingqc_colonies_bleached_obs.sample_unit_id = pseudosu_su.sample_unit_id)
                GROUP BY pseudosu_id, observers
            ) bleachingqc_obs_obs
            GROUP BY pseudosu_id
        ),
        qbp AS (
            SELECT pseudosu_id,
            COUNT(quadrat_number) AS quadrat_count,
            ROUND(AVG(percent_hard), 1) AS percent_hard_avg,
            ROUND(STDDEV(percent_hard), 1) AS percent_hard_sd,
            ROUND(AVG(percent_soft), 1) AS percent_soft_avg,
            ROUND(STDDEV(percent_soft), 1) AS percent_soft_sd,
            ROUND(AVG(percent_algae), 1) AS percent_algae_avg,
            ROUND(STDDEV(percent_algae), 1) AS percent_algae_sd
            FROM bleachingqc_quadrat_benthic_percent_obs
            INNER JOIN pseudosu_su 
                ON(bleachingqc_quadrat_benthic_percent_obs.sample_unit_id = pseudosu_su.sample_unit_id)
            GROUP BY pseudosu_id
        ),
        life_histories_agg AS (
            SELECT lh.pseudosu_id,
            jsonb_object_agg(
                lh.name,
                ROUND(
                    COALESCE(qbp.percent_hard_avg, 0) *
                    (
                        CASE WHEN colony_count.su_colony_count > 0 
                        THEN lh.proportion_sum / colony_count.su_colony_count
                        ELSE 0 END
                    ), 2
                )
            ) AS percent_cover_life_histories
            FROM (
                SELECT pseudosu_id,
                       life_history->>'id' AS id,
                       life_history->>'name' AS name,
                       SUM((life_history->>'proportion')::numeric * 
                           (count_normal + count_pale + count_20 + count_50 + count_80 + count_100 + count_dead)
                       ) AS proportion_sum
                FROM bleachingqc_colonies_bleached_obs
                INNER JOIN pseudosu_su 
                ON(bleachingqc_colonies_bleached_obs.sample_unit_id = pseudosu_su.sample_unit_id)
                CROSS JOIN jsonb_array_elements(life_histories) AS life_history
                WHERE benthic_category = 'Hard coral'
                GROUP BY pseudosu_id, life_history->>'id', life_history->>'name'
            ) lh
            INNER JOIN (
                SELECT pseudosu_id, 
                SUM(count_normal + count_pale + count_20 + count_50 + count_80 + count_100 + count_dead) AS su_colony_count
                FROM bleachingqc_colonies_bleached_obs
                INNER JOIN pseudosu_su 
                ON(bleachingqc_colonies_bleached_obs.sample_unit_id = pseudosu_su.sample_unit_id)
                WHERE benthic_category = 'Hard coral'
                GROUP BY pseudosu_id
            ) colony_count
            ON lh.pseudosu_id = colony_count.pseudosu_id
            LEFT JOIN qbp ON lh.pseudosu_id = qbp.pseudosu_id
            GROUP BY lh.pseudosu_id
        ) 

        SELECT NULL AS id,
        bleachingqc_su.pseudosu_id,
        {_su_fields},
        bleachingqc_su.{_agg_su_fields},
        count_genera,
        count_total,
        percent_normal,
        percent_pale,
        percent_20,
        percent_50,
        percent_80,
        percent_100,
        percent_dead,
        percent_bleached,
        quadrat_count,
        percent_hard_avg,
        percent_hard_sd,
        percent_soft_avg,
        percent_soft_sd,
        percent_algae_avg,
        percent_algae_sd,
        percent_cover_life_histories
        FROM (
            SELECT pseudosu_id,
            jsonb_agg(DISTINCT pseudosu_su.sample_unit_id) AS sample_unit_ids,
            {_su_fields_qualified},
            {_su_aggfields_sql},
            COUNT(DISTINCT benthic_attribute) AS count_genera,
            SUM(count_normal + count_pale + count_20 + count_50 + count_80 + count_100 + count_dead) AS count_total,
			ROUND(
				100 * (SUM(count_normal)::decimal /
				COALESCE(NULLIF(SUM(count_normal + count_pale + count_20 + count_50 + count_80 + count_100 + count_dead), 0), 1)
				), 1) AS percent_normal,
			ROUND(
				100 * (SUM(count_pale)::decimal /
				COALESCE(NULLIF(SUM(count_normal + count_pale + count_20 + count_50 + count_80 + count_100 + count_dead), 0), 1)
				), 1) AS percent_pale,
			ROUND(
				100 * (SUM(count_20)::decimal /
				COALESCE(NULLIF(SUM(count_normal + count_pale + count_20 + count_50 + count_80 + count_100 + count_dead), 0), 1)
				), 1) AS percent_20,
			ROUND(
				100 * (SUM(count_50)::decimal /
				COALESCE(NULLIF(SUM(count_normal + count_pale + count_20 + count_50 + count_80 + count_100 + count_dead), 0), 1)
				), 1) AS percent_50,
			ROUND(
				100 * (SUM(count_80)::decimal /
				COALESCE(NULLIF(SUM(count_normal + count_pale + count_20 + count_50 + count_80 + count_100 + count_dead), 0), 1)
				), 1) AS percent_80,
			ROUND(
				100 * (SUM(count_100)::decimal /
				COALESCE(NULLIF(SUM(count_normal + count_pale + count_20 + count_50 + count_80 + count_100 + count_dead), 0), 1)
				), 1) AS percent_100,
			ROUND(
				100 * (SUM(count_dead)::decimal /
				COALESCE(NULLIF(SUM(count_normal + count_pale + count_20 + count_50 + count_80 + count_100 + count_dead), 0), 1)
				), 1) AS percent_dead,
            ROUND(
                100 * (SUM(count_20 + count_50 + count_80 + count_100 + count_dead)::decimal /
				COALESCE(NULLIF(SUM(count_normal + count_pale + count_20 + count_50 + count_80 + count_100 + count_dead), 0), 1)
				), 1) AS percent_bleached
            
            FROM bleachingqc_colonies_bleached_obs
            INNER JOIN pseudosu_su ON(bleachingqc_colonies_bleached_obs.sample_unit_id = pseudosu_su.sample_unit_id)
            GROUP BY pseudosu_id,
            {_su_fields_qualified}
        ) bleachingqc_su
        INNER JOIN life_histories_agg
        ON (bleachingqc_su.pseudosu_id = life_histories_agg.pseudosu_id)
        INNER JOIN bleachingqc_observers
            ON (bleachingqc_su.pseudosu_id = bleachingqc_observers.pseudosu_id)
        LEFT JOIN qbp ON bleachingqc_su.pseudosu_id = qbp.pseudosu_id
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

    quadrat_size = models.DecimalField(decimal_places=2, max_digits=6)
    count_genera = models.PositiveSmallIntegerField(default=0)
    count_total = models.PositiveSmallIntegerField(default=0)
    percent_normal = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    percent_pale = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    percent_20 = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    percent_50 = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    percent_80 = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    percent_100 = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    percent_dead = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    percent_bleached = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    quadrat_count = models.PositiveSmallIntegerField(default=0)
    percent_hard_avg = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    percent_hard_sd = models.DecimalField(
        max_digits=4, decimal_places=1, default=0, null=True, blank=True
    )
    percent_soft_avg = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    percent_soft_sd = models.DecimalField(
        max_digits=4, decimal_places=1, default=0, null=True, blank=True
    )
    percent_algae_avg = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    percent_algae_sd = models.DecimalField(
        max_digits=4, decimal_places=1, default=0, null=True, blank=True
    )
    percent_cover_life_histories = models.JSONField(null=True, blank=True)
    data_policy_bleachingqc = models.CharField(max_length=50)
    pseudosu_id = models.UUIDField()

    class Meta:
        db_table = "bleachingqc_su_sm"
        managed = False


class BleachingQCSESQLModel(BaseSQLModel):
    _se_fields = ", ".join([f"bleachingqc_su.{f}" for f in BaseSQLModel.se_fields])
    _su_aggfields_sql = BaseSQLModel.su_aggfields_sql

    sql = f"""
        WITH bleachingqc_su AS (
            {BleachingQCSUSQLModel.sql}
        ),
        se_observers AS (
            SELECT sample_event_id,
            jsonb_agg(DISTINCT observer ORDER BY observer) AS observers
            FROM (
                SELECT sample_event_id, jsonb_array_elements(observers) AS observer
                FROM bleachingqc_su
            ) AS su_observers
            GROUP BY sample_event_id
        )
        SELECT bleachingqc_su.sample_event_id AS id,
        {_se_fields},
        data_policy_bleachingqc,
        se_observers.observers,
        {_su_aggfields_sql},
        COUNT(pseudosu_id) AS sample_unit_count,
        ROUND(AVG(quadrat_size), 1) AS quadrat_size_avg,
        ROUND(AVG(count_total), 1) AS count_total_avg,
        ROUND(STDDEV(count_total), 1) AS count_total_sd,
        ROUND(AVG(count_genera), 1) AS count_genera_avg,
        ROUND(STDDEV(count_genera), 1) AS count_genera_sd,
        ROUND(AVG(percent_normal), 1) AS percent_normal_avg,
        ROUND(STDDEV(percent_normal), 1) AS percent_normal_sd,
        ROUND(AVG(percent_pale), 1) AS percent_pale_avg,
        ROUND(STDDEV(percent_pale), 1) AS percent_pale_sd,
        ROUND(AVG(percent_20), 1) AS percent_20_avg,
        ROUND(STDDEV(percent_20), 1) AS percent_20_sd,
        ROUND(AVG(percent_50), 1) AS percent_50_avg,
        ROUND(STDDEV(percent_50), 1) AS percent_50_sd,
        ROUND(AVG(percent_80), 1) AS percent_80_avg,
        ROUND(STDDEV(percent_80), 1) AS percent_80_sd,
        ROUND(AVG(percent_100), 1) AS percent_100_avg,
        ROUND(STDDEV(percent_100), 1) AS percent_100_sd,
        ROUND(AVG(percent_dead), 1) AS percent_dead_avg,
        ROUND(STDDEV(percent_dead), 1) AS percent_dead_sd,
        ROUND(AVG(percent_bleached), 1) AS percent_bleached_avg,
        ROUND(STDDEV(percent_bleached), 1) AS percent_bleached_sd,
        ROUND(AVG(quadrat_count), 1) AS quadrat_count_avg,
        ROUND(AVG(percent_hard_avg), 1) AS percent_hard_avg_avg,
        ROUND(STDDEV(percent_hard_avg), 1) AS percent_hard_avg_sd,
        ROUND(AVG(percent_soft_avg), 1) AS percent_soft_avg_avg,
        ROUND(STDDEV(percent_soft_avg), 1) AS percent_soft_avg_sd,
        ROUND(AVG(percent_algae_avg), 1) AS percent_algae_avg_avg,
        ROUND(STDDEV(percent_algae_avg), 1) AS percent_algae_avg_sd,
        percent_cover_life_histories_avg,
        percent_cover_life_histories_sd

        FROM bleachingqc_su
        INNER JOIN se_observers ON (bleachingqc_su.sample_event_id = se_observers.sample_event_id)
        INNER JOIN (
            SELECT sample_event_id,
            jsonb_object_agg(bleachingqc_su_lh.name, ROUND(proportion_avg :: numeric, 2)) AS percent_cover_life_histories_avg,
            jsonb_object_agg(bleachingqc_su_lh.name, ROUND(proportion_sd :: numeric, 2)) AS percent_cover_life_histories_sd
            FROM (
                SELECT sample_event_id,
                life_history.key AS name,
                AVG(life_history.value :: float) AS proportion_avg,
                STDDEV(life_history.value :: float) AS proportion_sd
                FROM bleachingqc_su, 
                jsonb_each_text(percent_cover_life_histories) AS life_history
                GROUP BY sample_event_id, life_history.key
            ) AS bleachingqc_su_lh
            GROUP BY sample_event_id
        ) AS bleachingqc_se_lhs
        ON bleachingqc_su.sample_event_id = bleachingqc_se_lhs.sample_event_id
        GROUP BY
        {_se_fields},
        data_policy_bleachingqc,
        se_observers.observers,
        percent_cover_life_histories_avg,
        percent_cover_life_histories_sd
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
    quadrat_size_avg = models.DecimalField(decimal_places=2, max_digits=6)
    count_total_avg = models.DecimalField(max_digits=5, decimal_places=1)
    count_total_sd = models.DecimalField(max_digits=5, decimal_places=1, blank=True, null=True)
    count_genera_avg = models.DecimalField(max_digits=4, decimal_places=1)
    count_genera_sd = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
    percent_normal_avg = models.DecimalField(max_digits=4, decimal_places=1)
    percent_normal_sd = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
    percent_pale_avg = models.DecimalField(max_digits=4, decimal_places=1)
    percent_pale_sd = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
    percent_20_avg = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    percent_20_sd = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
    percent_50_avg = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    percent_50_sd = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
    percent_80_avg = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    percent_80_sd = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
    percent_100_avg = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    percent_100_sd = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
    percent_dead_avg = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    percent_dead_sd = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
    percent_bleached_avg = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    percent_bleached_sd = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
    quadrat_count_avg = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    percent_hard_avg_avg = models.DecimalField(
        max_digits=4, decimal_places=1, null=True, blank=True
    )
    percent_hard_avg_sd = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    percent_soft_avg_avg = models.DecimalField(
        max_digits=4, decimal_places=1, null=True, blank=True
    )
    percent_soft_avg_sd = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    percent_algae_avg_avg = models.DecimalField(
        max_digits=4, decimal_places=1, null=True, blank=True
    )
    percent_algae_avg_sd = models.DecimalField(
        max_digits=4, decimal_places=1, null=True, blank=True
    )
    percent_cover_life_histories_avg = models.JSONField(null=True, blank=True)
    percent_cover_life_histories_sd = models.JSONField(null=True, blank=True)
    data_policy_bleachingqc = models.CharField(max_length=50)

    class Meta:
        db_table = "bleachingqc_se_sm"
        managed = False
