from django.contrib.gis.db import models
from django.utils.translation import gettext_lazy as _

from sqltables import SQLTableArg, SQLTableManager
from .base import (
    BaseSQLModel,
    BaseSUSQLModel,
    project_where,
    sample_event_sql_template,
    sample_event_where
)


class BeltFishObsSQLModel(BaseSUSQLModel):
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
                FROM transect_belt_fish su
                JOIN se ON su.sample_event_id = se.sample_event_id
                GROUP BY {", ".join(BaseSUSQLModel.transect_su_fields)}
            ) pseudosu
        ) 
        SELECT o.id, pseudosu_id,
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
                power((o.size * f.biomass_constant_c)::float, f.biomass_constant_b::float)::numeric /
                (su.len_surveyed * wc.val)::numeric,
                2
            )::numeric AS biomass_kgha,
            o.notes AS observation_notes
        FROM obs_transectbeltfish o
            RIGHT JOIN transectmethod_transectbeltfish tt ON o.beltfish_id = tt.transectmethod_ptr_id
            JOIN transect_belt_fish su ON tt.transect_id = su.id
            JOIN se ON su.sample_event_id = se.sample_event_id
            JOIN pseudosu_su ON (su.id = pseudosu_su.sample_unit_id)
            JOIN vw_fish_attributes f ON o.fish_attribute_id = f.id
            JOIN api_belttransectwidth w ON su.width_id = w.id
            JOIN api_belttransectwidthcondition wc ON (
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
                    JOIN transectmethod_transectbeltfish tt_1 ON tm.id = tt_1.transectmethod_ptr_id
                    JOIN transect_belt_fish as tbf ON tt_1.transect_id = tbf.id
                    JOIN se ON tbf.sample_event_id = se.sample_event_id
                GROUP BY tt_1.transect_id) observers ON su.id = observers.transect_id
            LEFT JOIN api_current c ON su.current_id = c.id
            LEFT JOIN api_tide t ON su.tide_id = t.id
            LEFT JOIN api_visibility v ON su.visibility_id = v.id
            LEFT JOIN api_relativedepth r ON su.relative_depth_id = r.id
            LEFT JOIN api_fishsizebin sb ON su.size_bin_id = sb.id
            LEFT JOIN api_reefslope rs ON su.reef_slope_id = rs.id
        """

    sql_args = dict(
        project_id=SQLTableArg(sql=project_where, required=True),
        sample_event_id=SQLTableArg(sql=sample_event_where, required=False),
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
    pseudosu_id = models.UUIDField()

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

    # biomass_kgha_by_trophic_group_zeroes: object field
    # with biomass sum or 0 for every trophic group used by at least one observation
    # (not just TGs in that SU)
    # SE sql then produces mean per TG of all SUs in the SE
    # even if some SUs don't have that TG
    sql = f"""
        WITH beltfish_obs AS (
            SELECT * FROM summary_belt_fish_obs WHERE project_id = '%(project_id)s'::uuid
        ),
        
		beltfish_su_tg_all AS MATERIALIZED (SELECT
			pseudosu_id, fish_group_trophic.name AS trophic_group
			FROM fish_group_trophic CROSS JOIN beltfish_obs
			GROUP BY pseudosu_id, fish_group_trophic.name
		),
		beltfish_su_tg AS MATERIALIZED (SELECT 
			pseudosu_id,
			trophic_group,
			COALESCE(SUM(biomass_kgha), 0::numeric) AS biomass_kgha
			FROM beltfish_obs
			GROUP BY pseudosu_id, trophic_group
		),
		beltfish_su_family_all AS MATERIALIZED (SELECT
		    pseudosu_id, fish_family.name AS fish_family
		    FROM fish_family CROSS JOIN beltfish_obs
		    GROUP BY pseudosu_id, fish_family.name
		),
		beltfish_su_family AS MATERIALIZED (SELECT
            pseudosu_id,
            fish_family,
            COALESCE(SUM(biomass_kgha), 0::numeric) AS biomass_kgha
            FROM beltfish_obs
            GROUP BY pseudosu_id, fish_family
        ),
        
		beltfish_tg AS MATERIALIZED (SELECT
            beltfish_su_tg.pseudosu_id,
			jsonb_object_agg(
                CASE
                    WHEN beltfish_su_tg.trophic_group IS NULL THEN 'other'::character varying
                    ELSE beltfish_su_tg.trophic_group
                END, ROUND(beltfish_su_tg.biomass_kgha, 2)
            ) AS biomass_kgha_by_trophic_group,
            jsonb_object_agg(
                beltfish_su_tg_zeroes.trophic_group, 
				ROUND(beltfish_su_tg_zeroes.biomass_kgha, 2)
            ) AS biomass_kgha_by_trophic_group_zeroes

            FROM beltfish_su_tg
			INNER JOIN (
                SELECT 
				beltfish_su_tg_all.pseudosu_id,
				beltfish_su_tg_all.trophic_group,
				COALESCE(beltfish_su_tg.biomass_kgha, 0) AS biomass_kgha
				FROM beltfish_su_tg_all 
				LEFT JOIN beltfish_su_tg ON(
					beltfish_su_tg_all.pseudosu_id = beltfish_su_tg.pseudosu_id 
					AND beltfish_su_tg_all.trophic_group = beltfish_su_tg.trophic_group
				)
            ) beltfish_su_tg_zeroes
			ON(beltfish_su_tg.pseudosu_id = beltfish_su_tg_zeroes.pseudosu_id)
			GROUP BY beltfish_su_tg.pseudosu_id
        ),
        
		beltfish_families AS MATERIALIZED (SELECT
            beltfish_su_family.pseudosu_id,
            jsonb_object_agg(
                CASE
                    WHEN beltfish_su_family.fish_family IS NULL THEN 'other'::character varying
                    ELSE beltfish_su_family.fish_family
                END, ROUND(beltfish_su_family.biomass_kgha, 2)
            ) AS biomass_kgha_by_fish_family,
            jsonb_object_agg(
                beltfish_su_family_zeroes.fish_family,
                ROUND(beltfish_su_family_zeroes.biomass_kgha, 2)
            ) AS biomass_kgha_by_fish_family_zeroes
    
            FROM beltfish_su_family
            INNER JOIN (
                SELECT 
                beltfish_su_family_all.pseudosu_id,
                beltfish_su_family_all.fish_family,
                COALESCE(beltfish_su_family.biomass_kgha, 0) AS biomass_kgha
                FROM beltfish_su_family_all
                LEFT JOIN beltfish_su_family ON(
                    beltfish_su_family_all.pseudosu_id = beltfish_su_family.pseudosu_id
                    AND beltfish_su_family_all.fish_family = beltfish_su_family.fish_family
                )
            ) beltfish_su_family_zeroes
            ON(beltfish_su_family.pseudosu_id = beltfish_su_family_zeroes.pseudosu_id)
            GROUP BY beltfish_su_family.pseudosu_id
        ),

        beltfish_observers AS (
            SELECT pseudosu_id,
            jsonb_agg(DISTINCT observer) AS observers
            FROM (
                SELECT pseudosu_id,
                jsonb_array_elements(observers) AS observer
                FROM beltfish_obs
                GROUP BY pseudosu_id, observers
            ) beltfish_obs_obs
            GROUP BY pseudosu_id
        )
        
        SELECT NULL AS id,
        beltfish_su.pseudosu_id,
        {_su_fields},
        beltfish_su.{_agg_su_fields},
        reef_slope,
        transect_width_name,
        size_bin,
        total_abundance,
        biomass_kgha,
        biomass_kgha_by_trophic_group,
        biomass_kgha_by_trophic_group_zeroes,
        biomass_kgha_by_fish_family,
        biomass_kgha_by_fish_family_zeroes

        FROM (
            SELECT pseudosu_id,
            jsonb_agg(DISTINCT sample_unit_id) AS sample_unit_ids,
            SUM(beltfish_obs.count) AS total_abundance,
            SUM(beltfish_obs.biomass_kgha) AS biomass_kgha,
            {_su_fields_qualified},
            {_su_aggfields_sql},
            string_agg(DISTINCT reef_slope::text, ', '::text ORDER BY (reef_slope::text)) AS reef_slope,
            string_agg(DISTINCT transect_width_name::text, ', '::text ORDER BY (transect_width_name::text)) AS
            transect_width_name,
            string_agg(DISTINCT size_bin::text, ', '::text ORDER BY (size_bin::text)) AS size_bin

            FROM beltfish_obs
            GROUP BY pseudosu_id,
            {_su_fields_qualified}
        ) beltfish_su

        INNER JOIN beltfish_tg
        ON (beltfish_su.pseudosu_id = beltfish_tg.pseudosu_id)
        INNER JOIN beltfish_families
        ON (beltfish_su.pseudosu_id = beltfish_families.pseudosu_id)
        INNER JOIN beltfish_observers
        ON (beltfish_su.pseudosu_id = beltfish_observers.pseudosu_id)
    """

    sql_args = dict(
        project_id=SQLTableArg(sql=project_where, required=True),
        sample_event_id=SQLTableArg(sql=sample_event_where, required=False),
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
    biomass_kgha_by_trophic_group = models.JSONField(null=True, blank=True)
    biomass_kgha_by_fish_family = models.JSONField(null=True, blank=True)
    data_policy_beltfish = models.CharField(max_length=50)
    pseudosu_id = models.UUIDField()
    biomass_kgha_by_trophic_group_zeroes = models.JSONField(null=True, blank=True)
    biomass_kgha_by_fish_family_zeroes = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "belt_fish_su_sm"
        managed = False


class BeltFishSESQLModel(BaseSQLModel):

    _se_fields = ", ".join([f"beltfish_su.{f}" for f in BaseSQLModel.se_fields])
    _su_aggfields_sql = BaseSQLModel.su_aggfields_sql

    sql = f"""
        WITH beltfish_su AS (
            SELECT * FROM summary_belt_fish_su WHERE project_id = '%(project_id)s'::uuid
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
            ) FILTER (WHERE biomass_kgha > 0) AS biomass_kgha_by_trophic_group_avg
            FROM (
                SELECT meta_su_tgs.sample_event_id, tg,
                AVG(biomass_kgha) AS biomass_kgha
                FROM (
                    SELECT sample_event_id, pseudosu_id, tgdata.key AS tg,
                    SUM(tgdata.value::double precision) AS biomass_kgha
                    FROM beltfish_su,
                    LATERAL jsonb_each_text(biomass_kgha_by_trophic_group_zeroes)
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
            ) FILTER (WHERE biomass_kgha > 0) AS biomass_kgha_by_fish_family_avg
            FROM (
                SELECT meta_su_ffs.sample_event_id, ff,
                AVG(biomass_kgha) AS biomass_kgha
                FROM (
                    SELECT sample_event_id, pseudosu_id, ffdata.key AS ff,
                    SUM(ffdata.value::double precision) AS biomass_kgha
                    FROM beltfish_su,
                    LATERAL jsonb_each_text(biomass_kgha_by_fish_family_zeroes)
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

    sql_args = dict(
        project_id=SQLTableArg(sql=project_where, required=True),
        sample_event_id=SQLTableArg(sql=sample_event_where, required=False),
    )

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
    biomass_kgha_by_trophic_group_avg = models.JSONField(null=True, blank=True)
    biomass_kgha_by_fish_family_avg = models.JSONField(null=True, blank=True)
    data_policy_beltfish = models.CharField(max_length=50)

    class Meta:
        db_table = "belt_fish_se_sm"
        managed = False
