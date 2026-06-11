from django.contrib.gis.db import models
from django.utils.translation import gettext_lazy as _

from sqltables import SQLTableArg, SQLTableManager
from .base import BaseSQLModel, BaseSUSQLModel, project_where, sample_event_sql_template


class BeltInvertObsSQLModel(BaseSUSQLModel):
    _se_fields = ", ".join([f"se.{f}" for f in BaseSUSQLModel.se_fields])
    _su_fields = BaseSUSQLModel.su_fields_sql
    _transect_su_fields = ", ".join(BaseSUSQLModel.transect_su_fields)

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
                FROM transect_belt_invert su
                JOIN se ON su.sample_event_id = se.sample_event_id
                GROUP BY {_transect_su_fields}
            ) pseudosu
        )
        SELECT o.id, pseudosu_id,
            {_se_fields},
            {_su_fields},
            se.data_policy_macroinvertebrate,
            su.number AS transect_number,
            su.len_surveyed AS transect_len_surveyed,
            w.name AS transect_width_name,
            w.val AS width_m,
            sb.val AS size_bin,
            COALESCE(
                igoi.name,
                iclass.name,
                iord.name,
                ifam.name,
                ige.name,
                ispg.name || ' ' || isp.name
            ) AS invert_attribute_name,
            o.invert_attribute_id,
            o.count,
            o.size,
            o.include
        FROM obs_transectbeltinvert o
            RIGHT JOIN transectmethod_transectbeltinvert tt ON o.beltinvert_id = tt.transectmethod_ptr_id
            JOIN transect_belt_invert su ON tt.transect_id = su.id
            JOIN se ON su.sample_event_id = se.sample_event_id
            JOIN pseudosu_su ON (su.id = pseudosu_su.sample_unit_id)
            JOIN invert_belt_transect_width w ON su.width_id = w.id
            LEFT JOIN invert_size_bin sb ON su.size_bin_id = sb.id
            LEFT JOIN invert_group_of_interest igoi ON o.invert_attribute_id = igoi.invertattribute_ptr_id
            LEFT JOIN invert_class iclass ON o.invert_attribute_id = iclass.invertattribute_ptr_id
            LEFT JOIN invert_order iord ON o.invert_attribute_id = iord.invertattribute_ptr_id
            LEFT JOIN invert_family ifam ON o.invert_attribute_id = ifam.invertattribute_ptr_id
            LEFT JOIN invert_genus ige ON o.invert_attribute_id = ige.invertattribute_ptr_id
            LEFT JOIN invert_species isp ON o.invert_attribute_id = isp.invertattribute_ptr_id
            LEFT JOIN invert_genus ispg ON isp.genus_id = ispg.invertattribute_ptr_id
            JOIN (
                SELECT tt_1.transect_id,
                    jsonb_agg(jsonb_build_object(
                        'id', p.id,
                        'name',
                        (COALESCE(p.first_name, ''::character varying)::text || ' '::text)
                        || COALESCE(p.last_name, ''::character varying)::text)
                    ) AS observers
                FROM observer o1
                    JOIN profile p ON o1.profile_id = p.id
                    JOIN transectmethod tm ON o1.transectmethod_id = tm.id
                    JOIN transectmethod_transectbeltinvert tt_1 ON tm.id = tt_1.transectmethod_ptr_id
                    JOIN transect_belt_invert AS tbi ON tt_1.transect_id = tbi.id
                    JOIN se ON tbi.sample_event_id = se.sample_event_id
                GROUP BY tt_1.transect_id) observers ON su.id = observers.transect_id
            LEFT JOIN api_current c ON su.current_id = c.id
            LEFT JOIN api_tide t ON su.tide_id = t.id
            LEFT JOIN api_visibility v ON su.visibility_id = v.id
            LEFT JOIN api_relativedepth r ON su.relative_depth_id = r.id
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
    transect_len_surveyed = models.DecimalField(max_digits=4, decimal_places=1)
    transect_width_name = models.CharField(max_length=100, null=True, blank=True)
    width_m = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    size_bin = models.CharField(max_length=100, null=True, blank=True)
    invert_attribute_id = models.UUIDField(null=True, blank=True)
    invert_attribute_name = models.CharField(max_length=200, null=True, blank=True)
    count = models.PositiveIntegerField(null=True, blank=True)
    size = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    include = models.BooleanField(null=True, blank=True)
    data_policy_macroinvertebrate = models.CharField(max_length=50)
    pseudosu_id = models.UUIDField()

    class Meta:
        db_table = "belt_invert_obs_sm"
        managed = False


class BeltInvertSUSQLModel(BaseSUSQLModel):
    su_fields = BaseSUSQLModel.se_fields + [
        "depth",
        "transect_number",
        "transect_len_surveyed",
        "data_policy_macroinvertebrate",
    ]

    _su_fields = ", ".join(su_fields)
    _su_fields_qualified = ", ".join([f"belt_invert_obs_all.{f}" for f in su_fields])
    _agg_su_fields = ", ".join(BaseSUSQLModel.agg_su_fields)
    _su_aggfields_sql = BaseSUSQLModel.su_aggfields_sql

    sql = f"""
        WITH belt_invert_obs_all AS (
            {BeltInvertObsSQLModel.sql}
        ),
        belt_invert_obs AS (
            SELECT * FROM belt_invert_obs_all WHERE include = TRUE
        ),
        goi_weights_by_family AS MATERIALIZED (
            SELECT ig.family_id, goi.name AS goi_name,
                COUNT(ig.invertattribute_ptr_id)::float /
                SUM(COUNT(ig.invertattribute_ptr_id)) OVER (PARTITION BY ig.family_id) AS weight
            FROM invert_genus ig
            JOIN invert_group_of_interest goi ON ig.group_of_interest_id = goi.invertattribute_ptr_id
            GROUP BY ig.family_id, ig.group_of_interest_id, goi.name
        ),
        goi_weights_by_order AS MATERIALIZED (
            SELECT io.invertattribute_ptr_id AS order_id, goi.name AS goi_name,
                COUNT(ig.invertattribute_ptr_id)::float /
                SUM(COUNT(ig.invertattribute_ptr_id)) OVER (PARTITION BY io.invertattribute_ptr_id) AS weight
            FROM invert_genus ig
            JOIN invert_family f ON ig.family_id = f.invertattribute_ptr_id
            JOIN invert_order io ON f.order_id = io.invertattribute_ptr_id
            JOIN invert_group_of_interest goi ON ig.group_of_interest_id = goi.invertattribute_ptr_id
            GROUP BY io.invertattribute_ptr_id, ig.group_of_interest_id, goi.name
        ),
        goi_weights_by_class AS MATERIALIZED (
            SELECT io.invert_class_id, goi.name AS goi_name,
                COUNT(ig.invertattribute_ptr_id)::float /
                SUM(COUNT(ig.invertattribute_ptr_id)) OVER (PARTITION BY io.invert_class_id) AS weight
            FROM invert_genus ig
            JOIN invert_family f ON ig.family_id = f.invertattribute_ptr_id
            JOIN invert_order io ON f.order_id = io.invertattribute_ptr_id
            JOIN invert_group_of_interest goi ON ig.group_of_interest_id = goi.invertattribute_ptr_id
            GROUP BY io.invert_class_id, ig.group_of_interest_id, goi.name
        ),
        obs_goi AS (
            SELECT o.pseudosu_id, goi.name AS goi_name, o.count::float AS attributed_count
            FROM belt_invert_obs o
            JOIN invert_group_of_interest goi ON o.invert_attribute_id = goi.invertattribute_ptr_id
            UNION ALL
            SELECT o.pseudosu_id, goi.name, o.count::float
            FROM belt_invert_obs o
            JOIN invert_species sp ON o.invert_attribute_id = sp.invertattribute_ptr_id
            JOIN invert_genus g ON sp.genus_id = g.invertattribute_ptr_id
            JOIN invert_group_of_interest goi ON g.group_of_interest_id = goi.invertattribute_ptr_id
            UNION ALL
            SELECT o.pseudosu_id, goi.name, o.count::float
            FROM belt_invert_obs o
            JOIN invert_genus g ON o.invert_attribute_id = g.invertattribute_ptr_id
            JOIN invert_group_of_interest goi ON g.group_of_interest_id = goi.invertattribute_ptr_id
            UNION ALL
            SELECT o.pseudosu_id, w.goi_name, o.count * w.weight
            FROM belt_invert_obs o
            JOIN invert_family fam ON o.invert_attribute_id = fam.invertattribute_ptr_id
            JOIN goi_weights_by_family w ON fam.invertattribute_ptr_id = w.family_id
            UNION ALL
            SELECT o.pseudosu_id, w.goi_name, o.count * w.weight
            FROM belt_invert_obs o
            JOIN invert_order ord ON o.invert_attribute_id = ord.invertattribute_ptr_id
            JOIN goi_weights_by_order w ON ord.invertattribute_ptr_id = w.order_id
            UNION ALL
            SELECT o.pseudosu_id, w.goi_name, o.count * w.weight
            FROM belt_invert_obs o
            JOIN invert_class cls ON o.invert_attribute_id = cls.invertattribute_ptr_id
            JOIN goi_weights_by_class w ON cls.invertattribute_ptr_id = w.invert_class_id
        ),
        su_goi AS MATERIALIZED (
            SELECT pseudosu_id, goi_name, SUM(attributed_count) AS goi_count
            FROM obs_goi GROUP BY pseudosu_id, goi_name
        ),
        su_goi_zeroes AS MATERIALIZED (
            SELECT a.pseudosu_id, a.goi_name, COALESCE(g.goi_count, 0) AS goi_count
            FROM (
                SELECT DISTINCT o.pseudosu_id, igoi.name AS goi_name
                FROM belt_invert_obs_all o CROSS JOIN invert_group_of_interest igoi
            ) a
            LEFT JOIN su_goi g USING (pseudosu_id, goi_name)
        ),
        su_goi_density_values AS MATERIALIZED (
            SELECT z.pseudosu_id, z.goi_name, z.goi_count,
                ROUND(
                    z.goi_count::numeric / NULLIF(sa.len_surveyed * sa.width_m, 0) * 10000, 2
                ) AS density
            FROM su_goi_zeroes z
            JOIN (
                SELECT pseudosu_id,
                    MAX(transect_len_surveyed)::numeric AS len_surveyed,
                    MAX(width_m)::numeric AS width_m
                FROM belt_invert_obs_all GROUP BY pseudosu_id
            ) sa USING (pseudosu_id)
        ),
        su_goi_density AS MATERIALIZED (
            SELECT pseudosu_id,
                jsonb_object_agg(goi_name, density)
                    FILTER (WHERE goi_count > 0) AS density_indha_group_interest,
                jsonb_object_agg(goi_name, density) AS density_indha_group_interest_zeroes
            FROM su_goi_density_values
            GROUP BY pseudosu_id
        ),
        beltinvert_observers AS (
            SELECT pseudosu_id,
            jsonb_agg(DISTINCT observer) AS observers
            FROM (
                SELECT pseudosu_id,
                jsonb_array_elements(observers) AS observer
                FROM belt_invert_obs_all
                GROUP BY pseudosu_id, observers
            ) beltinvert_obs_obs
            GROUP BY pseudosu_id
        )

        SELECT NULL AS id,
        beltinvert_su.pseudosu_id,
        {_su_fields},
        beltinvert_su.{_agg_su_fields},
        transect_width_name,
        size_bin,
        total_abundance,
        density_indha,
        density_indha_group_interest,
        density_indha_group_interest_zeroes

        FROM (
            SELECT pseudosu_id,
            jsonb_agg(DISTINCT sample_unit_id) AS sample_unit_ids,
            COALESCE(SUM(count) FILTER (WHERE include = TRUE), 0) AS total_abundance,
            ROUND(
                COALESCE(SUM(count) FILTER (WHERE include = TRUE), 0)::numeric /
                NULLIF((MAX(transect_len_surveyed) * MAX(width_m)), 0) * 10000, 2
            ) AS density_indha,
            {_su_fields_qualified},
            {_su_aggfields_sql},
            string_agg(DISTINCT transect_width_name::text, ', '::text
                ORDER BY (transect_width_name::text)) AS transect_width_name,
            string_agg(DISTINCT size_bin::text, ', '::text
                ORDER BY (size_bin::text)) AS size_bin

            FROM belt_invert_obs_all
            GROUP BY pseudosu_id,
            {_su_fields_qualified}
        ) beltinvert_su

        LEFT JOIN su_goi_density ON (beltinvert_su.pseudosu_id = su_goi_density.pseudosu_id)
        INNER JOIN beltinvert_observers ON (beltinvert_su.pseudosu_id = beltinvert_observers.pseudosu_id)
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
    total_abundance = models.PositiveIntegerField()
    transect_number = models.PositiveSmallIntegerField()
    transect_len_surveyed = models.DecimalField(max_digits=4, decimal_places=1)
    transect_width_name = models.CharField(max_length=100, null=True, blank=True)
    size_bin = models.CharField(max_length=100, null=True, blank=True)
    density_indha = models.DecimalField(max_digits=11, decimal_places=2, null=True, blank=True)
    density_indha_group_interest = models.JSONField(null=True, blank=True)
    density_indha_group_interest_zeroes = models.JSONField(null=True, blank=True)
    data_policy_macroinvertebrate = models.CharField(max_length=50)
    pseudosu_id = models.UUIDField()

    class Meta:
        db_table = "belt_invert_su_sm"
        managed = False


class BeltInvertSESQLModel(BaseSQLModel):
    _se_fields = ", ".join([f"belt_invert_su.{f}" for f in BaseSQLModel.se_fields])
    _su_aggfields_sql = BaseSQLModel.su_aggfields_sql

    sql = f"""
        WITH belt_invert_su AS (
            {BeltInvertSUSQLModel.sql}
        ),
        se_observers AS (
            SELECT sample_event_id,
            jsonb_agg(DISTINCT observer ORDER BY observer) AS observers
            FROM (
                SELECT sample_event_id, jsonb_array_elements(observers) AS observer
                FROM belt_invert_su
            ) AS su_observers
            GROUP BY sample_event_id
        )

        SELECT belt_invert_su.sample_event_id AS id,
        {_se_fields},
        data_policy_macroinvertebrate,
        se_observers.observers,
        {_su_aggfields_sql},
        COUNT(belt_invert_su.pseudosu_id) AS sample_unit_count,
        ROUND(AVG(belt_invert_su.total_abundance), 1) AS count_total_avg,
        ROUND(STDDEV(belt_invert_su.total_abundance), 1) AS count_total_sd,
        ROUND(AVG(belt_invert_su.density_indha), 2) AS density_indha_avg,
        ROUND(STDDEV(belt_invert_su.density_indha), 2) AS density_indha_sd,
        density_indha_group_interest_avg,
        density_indha_group_interest_sd

        FROM belt_invert_su

        LEFT JOIN (
            SELECT sample_event_id,
            jsonb_object_agg(goi, ROUND(density_avg::numeric, 2))
                FILTER (WHERE density_avg > 0) AS density_indha_group_interest_avg,
            jsonb_object_agg(goi, ROUND(density_sd::numeric, 2))
                FILTER (WHERE density_avg > 0) AS density_indha_group_interest_sd
            FROM (
                SELECT sample_event_id, goi,
                AVG(density) AS density_avg,
                STDDEV(density) AS density_sd
                FROM (
                    SELECT sample_event_id, pseudosu_id, gdata.key AS goi,
                    SUM(gdata.value::double precision) AS density
                    FROM belt_invert_su,
                    LATERAL jsonb_each_text(density_indha_group_interest_zeroes) gdata(key, value)
                    GROUP BY sample_event_id, pseudosu_id, gdata.key
                ) mi_goi_su
                GROUP BY sample_event_id, goi
            ) mi_goi
            GROUP BY sample_event_id
        ) migoi ON (belt_invert_su.sample_event_id = migoi.sample_event_id)

        INNER JOIN se_observers ON (belt_invert_su.sample_event_id = se_observers.sample_event_id)

        GROUP BY
        {_se_fields},
        data_policy_macroinvertebrate,
        density_indha_group_interest_avg,
        density_indha_group_interest_sd,
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
    current_name = models.CharField(max_length=100, null=True, blank=True)
    tide_name = models.CharField(max_length=100, null=True, blank=True)
    visibility_name = models.CharField(max_length=100, null=True, blank=True)
    count_total_avg = models.DecimalField(
        max_digits=11,
        decimal_places=1,
        null=True,
        blank=True,
    )
    count_total_sd = models.DecimalField(
        max_digits=11,
        decimal_places=1,
        null=True,
        blank=True,
    )
    density_indha_avg = models.DecimalField(
        max_digits=11,
        decimal_places=2,
        null=True,
        blank=True,
    )
    density_indha_sd = models.DecimalField(
        max_digits=11,
        decimal_places=2,
        null=True,
        blank=True,
    )
    density_indha_group_interest_avg = models.JSONField(null=True, blank=True)
    density_indha_group_interest_sd = models.JSONField(null=True, blank=True)
    data_policy_macroinvertebrate = models.CharField(max_length=50)

    class Meta:
        db_table = "belt_invert_se_sm"
        managed = False
