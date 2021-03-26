from django.contrib.gis.db import models
from django.contrib.postgres.fields import JSONField
from django.utils.translation import ugettext_lazy as _

from sqltables import SQLTableArg, SQLTableManager
from .base import BaseSQLModel, BaseSUSQLModel, sample_event_sql_template


class BeltFishObsSQLModel(BaseSUSQLModel):

    _se_fields = ", ".join([f"se.{f}" for f in BaseSUSQLModel.se_fields])
    _su_fields = BaseSUSQLModel.su_fields_sql
    sql = f"""
        SELECT o.id,
            {_se_fields},
            {_su_fields},
            se.data_policy_beltfish,
            su.number AS transect_number,
            su.len_surveyed AS transect_len_surveyed,
            rs.name AS reef_slope,
            w.name AS transect_width_name,
            f.id_family AS id_family,
            f.id_genus AS id_genus,
            f.id_species AS id_species,
            f.name_family AS fish_family,
            f.name_genus AS fish_genus,
            f.name AS fish_taxon,
            f.trophic_group,
            f.trophic_level,
            f.functional_group,
            f.vulnerability,
            f.biomass_constant_a,
            f.biomass_constant_b,
            f.biomass_constant_c,
            sb.val AS size_bin,
            o.size,
            o.count,
            ROUND(
                (10 * o.count)::numeric * f.biomass_constant_a *
                ((o.size * f.biomass_constant_c) ^ f.biomass_constant_b) /
                (su.len_surveyed * wc.val)::numeric,
                2
            )::numeric AS biomass_kgha,
            o.notes AS observation_notes
        FROM obs_transectbeltfish o
            JOIN vw_fish_attributes f ON o.fish_attribute_id = f.id
            RIGHT JOIN transectmethod_transectbeltfish tt
            ON o.beltfish_id = tt.transectmethod_ptr_id
            JOIN transect_belt_fish su ON tt.transect_id = su.id
            LEFT JOIN api_current c ON su.current_id = c.id
            LEFT JOIN api_tide t ON su.tide_id = t.id
            LEFT JOIN api_visibility v ON su.visibility_id = v.id
            LEFT JOIN api_relativedepth r ON su.relative_depth_id = r.id
            LEFT JOIN api_fishsizebin sb ON su.size_bin_id = sb.id
            LEFT JOIN api_reefslope rs ON su.reef_slope_id = rs.id
            JOIN api_belttransectwidth w ON su.width_id = w.id
            INNER JOIN api_belttransectwidthcondition wc ON (
                w.id = wc.belttransectwidth_id
                AND (
                    ((wc.operator = '<' AND o.size < wc.size)
                    OR (wc.operator IS NULL AND wc.size IS NULL))
                    OR ((wc.operator = '<=' AND o.size <= wc.size)
                    OR (wc.operator IS NULL AND wc.size IS NULL))
                    OR ((wc.operator = '>' AND o.size > wc.size)
                    OR (wc.operator IS NULL AND wc.size IS NULL))
                    OR ((wc.operator = '>=' AND o.size >= wc.size)
                    OR (wc.operator IS NULL AND wc.size IS NULL))
                    OR ((wc.operator = '==' AND o.size = wc.size)
                    OR (wc.operator IS NULL AND wc.size IS NULL))
                    OR ((wc.operator = '!=' AND o.size != wc.size)
                    OR (wc.operator IS NULL AND wc.size IS NULL))
                )
            )
            JOIN ( SELECT tt_1.transect_id,
                    jsonb_agg(jsonb_build_object(
                        'id', p.id,
                        'name',
                        (COALESCE(p.first_name, ''::character varying)::text || ' '::text)
                        || COALESCE(p.last_name, ''::character varying)::text)
                    ) AS observers
                FROM observer o1
                    JOIN profile p ON o1.profile_id = p.id
                    JOIN transectmethod tm ON o1.transectmethod_id = tm.id
                    JOIN transectmethod_transectbeltfish tt_1
                    ON tm.id = tt_1.transectmethod_ptr_id
                GROUP BY tt_1.transect_id) observers ON su.id = observers.transect_id
            JOIN ({sample_event_sql_template}) se
            ON su.sample_event_id = se.sample_event_id
    """

    sql_args = dict(project_id=SQLTableArg(required=True))

    objects = SQLTableManager()

    sample_unit_id = models.UUIDField()
    transect_number = models.PositiveSmallIntegerField()
    transect_len_surveyed = models.PositiveSmallIntegerField(
        verbose_name=_("transect length surveyed (m)")
    )
    transect_width_name = models.CharField(max_length=100, null=True, blank=True)
    reef_slope = models.CharField(max_length=50)
    fish_family = models.CharField(max_length=100, null=True, blank=True)
    fish_genus = models.CharField(max_length=100, null=True, blank=True)
    fish_taxon = models.CharField(max_length=100, null=True, blank=True)
    trophic_group = models.CharField(max_length=100, blank=True)
    trophic_level = models.DecimalField(
        max_digits=3, decimal_places=2, null=True, blank=True
    )
    functional_group = models.CharField(max_length=100, blank=True)
    vulnerability = models.DecimalField(
        max_digits=4, decimal_places=2, null=True, blank=True
    )
    biomass_constant_a = models.DecimalField(
        max_digits=7, decimal_places=6, null=True, blank=True
    )
    biomass_constant_b = models.DecimalField(
        max_digits=7, decimal_places=6, null=True, blank=True
    )
    biomass_constant_c = models.DecimalField(
        max_digits=7, decimal_places=6, default=1, null=True, blank=True
    )
    size_bin = models.CharField(max_length=100)
    size = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        verbose_name=_("size (cm)"),
        null=True,
        blank=True,
    )
    count = models.PositiveIntegerField(default=1, null=True, blank=True)
    biomass_kgha = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        verbose_name=_("biomass (kg/ha)"),
        null=True,
        blank=True,
    )
    observation_notes = models.TextField(blank=True)
    data_policy_beltfish = models.CharField(max_length=50)

    class Meta:
        db_table = "belt_fish_obs_sm"
        managed = False


class BeltFishSUSQLModel(BaseSUSQLModel):

    # Unique combination of these fields defines a single (pseudo) sample unit.
    # All other fields are aggregated.
    su_fields = BaseSUSQLModel.se_fields + [
        "depth",
        "transect_number",
        "transect_len_surveyed",
        "data_policy_beltfish",
    ]

    _su_fields = ", ".join(su_fields)
    _su_fields_qualified = ", ".join([f"beltfish_obs.{f}" for f in su_fields])
    _agg_su_fields = ", ".join(BaseSUSQLModel.agg_su_fields)
    _su_aggfields_sql = BaseSUSQLModel.su_aggfields_sql

    sql = f"""
        WITH beltfish_obs AS (
            {BeltFishObsSQLModel.sql}
        )
        SELECT NULL AS id,
        uuid_generate_v4() AS pseudosu_id,
        {_su_fields},
        beltfish_su.{_agg_su_fields},
        reef_slope,
        transect_width_name,
        size_bin,
        total_abundance,
        biomass_kgha,
        biomass_kgha_by_trophic_group,
        biomass_kgha_by_fish_family

        FROM (
            SELECT 
            jsonb_agg(DISTINCT sample_unit_id) AS sample_unit_ids,
            SUM(beltfish_obs.count) AS total_abundance,
            {_su_fields_qualified},
            {_su_aggfields_sql},
            string_agg(DISTINCT reef_slope::text, ', '::text ORDER BY (reef_slope::text)) AS reef_slope,
            string_agg(DISTINCT transect_width_name::text, ', '::text ORDER BY (transect_width_name::text)) AS
            transect_width_name,
            string_agg(DISTINCT size_bin::text, ', '::text ORDER BY (size_bin::text)) AS size_bin

            FROM beltfish_obs
            GROUP BY 
            {_su_fields_qualified}
        ) beltfish_su

        INNER JOIN (
            SELECT jsonb_agg(DISTINCT sample_unit_id) AS sample_unit_ids,
            SUM(biomass_kgha) AS biomass_kgha,
            jsonb_object_agg(
                CASE
                    WHEN trophic_group IS NULL THEN 'other'::character varying
                    ELSE trophic_group
                END, ROUND(biomass_kgha, 2)
            ) AS biomass_kgha_by_trophic_group

            FROM (
                SELECT sample_unit_id,
                {_su_fields},
                COALESCE(SUM(biomass_kgha), 0::numeric) AS biomass_kgha,
                trophic_group
                FROM beltfish_obs
                GROUP BY {_su_fields}, sample_unit_id,
                trophic_group
            ) beltfish_obs_tg
            GROUP BY {_su_fields}
        ) beltfish_tg
        ON (beltfish_su.sample_unit_ids = beltfish_tg.sample_unit_ids)

        INNER JOIN (
            SELECT jsonb_agg(DISTINCT sample_unit_id) AS sample_unit_ids,
            jsonb_object_agg(
                CASE
                    WHEN fish_family IS NULL THEN 'other'::character varying
                    ELSE fish_family
                END, ROUND(biomass_kgha, 2)
            ) AS biomass_kgha_by_fish_family
    
            FROM (
                SELECT sample_unit_id,
                {_su_fields},
                COALESCE(SUM(biomass_kgha), 0::numeric) AS biomass_kgha,
                fish_family
                FROM beltfish_obs
                GROUP BY {_su_fields}, sample_unit_id, 
                fish_family
            ) beltfish_obs_tg
            GROUP BY {_su_fields}
        ) beltfish_families
        ON (beltfish_su.sample_unit_ids = beltfish_families.sample_unit_ids)

        INNER JOIN (
            SELECT jsonb_agg(DISTINCT sample_unit_id) AS sample_unit_ids,
            jsonb_agg(DISTINCT observer) AS observers

            FROM (
                SELECT sample_unit_id,
                {_su_fields},
                jsonb_array_elements(observers) AS observer
                FROM beltfish_obs
                GROUP BY {_su_fields}, sample_unit_id,
                observers
            ) beltfish_obs_obs
            GROUP BY {_su_fields}
        ) beltfish_observers
        ON (beltfish_su.sample_unit_ids = beltfish_observers.sample_unit_ids)
    """

    sql_args = dict(project_id=SQLTableArg(required=True))

    objects = SQLTableManager()

    sample_unit_ids = JSONField()
    total_abundance = models.PositiveIntegerField()
    transect_number = models.PositiveSmallIntegerField()
    transect_len_surveyed = models.PositiveSmallIntegerField(
        verbose_name=_("transect length surveyed (m)")
    )
    transect_width_name = models.CharField(max_length=100, null=True, blank=True)
    reef_slope = models.CharField(max_length=50)
    size_bin = models.CharField(max_length=100)
    biomass_kgha = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name=_("biomass (kg/ha)"),
        null=True,
        blank=True,
    )
    biomass_kgha_by_trophic_group = JSONField(null=True, blank=True)
    biomass_kgha_by_fish_family = JSONField(null=True, blank=True)
    data_policy_beltfish = models.CharField(max_length=50)

    class Meta:
        db_table = "belt_fish_su_sm"
        managed = False


class BeltFishSESQLModel(BaseSQLModel):

    _se_fields = ", ".join([f"beltfish_su.{f}" for f in BaseSQLModel.se_fields])
    _su_aggfields_sql = BaseSQLModel.su_aggfields_sql

    sql = f"""
        WITH beltfish_su AS (
            {BeltFishSUSQLModel.sql}
        )
        -- For each SE, summarize biomass by 1) avg
        -- of transects and 2) avg of transects' trophic groups
        SELECT beltfish_su.sample_event_id AS id,
        {_se_fields},
        data_policy_beltfish,
        {_su_aggfields_sql},
        COUNT(beltfish_su.pseudosu_id) AS sample_unit_count,
        ROUND(AVG(beltfish_su.biomass_kgha), 2) AS biomass_kgha_avg,
        biomass_kgha_by_trophic_group_avg,
        biomass_kgha_by_fish_family_avg

        FROM beltfish_su

        INNER JOIN (
            SELECT sample_event_id,
            jsonb_object_agg(
                tg,
                ROUND(biomass_kgha::numeric, 2)
            ) AS biomass_kgha_by_trophic_group_avg
            FROM (
                SELECT meta_su_tgs.sample_event_id, tg,
                AVG(biomass_kgha) AS biomass_kgha
                FROM (
                    SELECT sample_event_id, pseudosu_id, tgdata.key AS tg,
                    SUM(tgdata.value::double precision) AS biomass_kgha
                    FROM beltfish_su,
                    LATERAL jsonb_each_text(biomass_kgha_by_trophic_group)
                    tgdata(key, value)
                    GROUP BY sample_event_id, pseudosu_id, tgdata.key
                ) meta_su_tgs
                GROUP BY meta_su_tgs.sample_event_id, tg
            ) beltfish_su_tg
            GROUP BY sample_event_id
        ) AS beltfish_se_tg
        ON beltfish_su.sample_event_id = beltfish_se_tg.sample_event_id

        INNER JOIN (
            SELECT sample_event_id,
            jsonb_object_agg(
                ff,
                ROUND(biomass_kgha::numeric, 2)
            ) AS biomass_kgha_by_fish_family_avg
            FROM (
                SELECT meta_su_ffs.sample_event_id, ff,
                AVG(biomass_kgha) AS biomass_kgha
                FROM (
                    SELECT sample_event_id, pseudosu_id, ffdata.key AS ff,
                    SUM(ffdata.value::double precision) AS biomass_kgha
                    FROM beltfish_su,
                    LATERAL jsonb_each_text(biomass_kgha_by_fish_family)
                    ffdata(key, value)
                    GROUP BY sample_event_id, pseudosu_id, ffdata.key
                ) meta_su_ffs
                GROUP BY meta_su_ffs.sample_event_id, ff
            ) beltfish_su_ff
            GROUP BY sample_event_id
        ) AS beltfish_se_fish_families
        ON beltfish_su.sample_event_id = beltfish_se_fish_families.sample_event_id

        GROUP BY
        {_se_fields},
        data_policy_beltfish,
        biomass_kgha_by_trophic_group_avg,
        biomass_kgha_by_fish_family_avg
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
    biomass_kgha_avg = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name=_("biomass (kg/ha)"),
        null=True,
        blank=True,
    )
    biomass_kgha_by_trophic_group_avg = JSONField(null=True, blank=True)
    biomass_kgha_by_fish_family_avg = JSONField(null=True, blank=True)
    data_policy_beltfish = models.CharField(max_length=50)

    class Meta:
        db_table = "belt_fish_se_sm"
        managed = False
