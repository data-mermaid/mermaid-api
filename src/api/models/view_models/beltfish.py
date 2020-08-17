from django.utils.translation import ugettext_lazy as _
from ..base import ExtendedManager
from .base import *


class BeltFishObsView(BaseSUViewModel):
    sql = """
CREATE OR REPLACE VIEW public.vw_beltfish_obs
 AS
 SELECT o.id,
    {se_fields},
    {su_fields},
    se.data_policy_beltfish,
    tt.transectmethod_ptr_id AS sample_unit_id,
    tm.number AS transect_number,
    tm.label,
    tm.len_surveyed AS transect_len_surveyed,
    rs.name AS reef_slope,
    w.name AS transect_width_name,
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
        (10 * o.count)::numeric * f.biomass_constant_a * ((o.size * f.biomass_constant_c) ^ f.biomass_constant_b) / 
        (tm.len_surveyed * wc.val)::numeric, 
        2
    )::numeric AS biomass_kgha,
    o.notes AS observation_notes
   FROM obs_transectbeltfish o
     JOIN vw_fish_attributes f ON o.fish_attribute_id = f.id
     RIGHT JOIN transectmethod_transectbeltfish tt ON o.beltfish_id = tt.transectmethod_ptr_id
     JOIN transect_belt_fish tm ON tt.transect_id = tm.id
     LEFT JOIN api_current c ON tm.current_id = c.id
     LEFT JOIN api_tide t ON tm.tide_id = t.id
     LEFT JOIN api_visibility v ON tm.visibility_id = v.id
     LEFT JOIN api_relativedepth r ON tm.relative_depth_id = r.id
     LEFT JOIN api_fishsizebin sb ON tm.size_bin_id = sb.id
     LEFT JOIN api_reefslope rs ON tm.reef_slope_id = rs.id
     JOIN api_belttransectwidth w ON tm.width_id = w.id
     INNER JOIN api_belttransectwidthcondition wc ON (
         w.id = wc.belttransectwidth_id 
         AND (
             ((wc.operator = '<' AND o.size < wc.size) OR (wc.operator IS NULL AND wc.size IS NULL))
             OR ((wc.operator = '<=' AND o.size <= wc.size) OR (wc.operator IS NULL AND wc.size IS NULL))
             OR ((wc.operator = '>' AND o.size > wc.size) OR (wc.operator IS NULL AND wc.size IS NULL))
             OR ((wc.operator = '>=' AND o.size >= wc.size) OR (wc.operator IS NULL AND wc.size IS NULL))
             OR ((wc.operator = '==' AND o.size = wc.size) OR (wc.operator IS NULL AND wc.size IS NULL))
             OR ((wc.operator = '!=' AND o.size != wc.size) OR (wc.operator IS NULL AND wc.size IS NULL))
         )
     )
     JOIN ( SELECT tt_1.transect_id,
            jsonb_agg(jsonb_build_object(
                'id', p.id,
                'name', (COALESCE(p.first_name, ''::character varying)::text || ' '::text) 
                || COALESCE(p.last_name, ''::character varying)::text)
            ) AS observers
           FROM observer o1
             JOIN profile p ON o1.profile_id = p.id
             JOIN transectmethod tm ON o1.transectmethod_id = tm.id
             JOIN transectmethod_transectbeltfish tt_1 ON tm.id = tt_1.transectmethod_ptr_id
          GROUP BY tt_1.transect_id) observers ON tm.id = observers.transect_id
     JOIN vw_sample_events se ON tm.sample_event_id = se.sample_event_id;
    """.format(
        se_fields=", ".join([f"se.{f}" for f in BaseSUViewModel.se_fields]),
        su_fields=BaseSUViewModel.su_fields_sql,
    )

    reverse_sql = "DROP VIEW IF EXISTS public.vw_beltfish_obs CASCADE;"

    sample_unit_id = models.UUIDField()
    transect_number = models.PositiveSmallIntegerField()
    label = models.CharField(max_length=50, blank=True)
    relative_depth = models.CharField(max_length=50)
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
        db_table = "vw_beltfish_obs"
        managed = False


class BeltFishSUView(BaseSUViewModel):
    project_lookup = "project_id"

    # Unique combination of these fields defines a single sample unit. All other fields are aggregated.
    su_fields = BaseSUViewModel.se_fields + ["depth", "transect_number", "transect_len_surveyed", "data_policy_beltfish"]
    su_tg_join = " AND ".join([
        f"(beltfish_su.{f} = beltfish_tg.{f} OR (beltfish_su.{f} IS NULL AND beltfish_tg.{f} IS NULL))"
        for f in su_fields
    ])
    su_obs_join = " AND ".join([
        f"(beltfish_su.{f} = beltfish_obs.{f} OR (beltfish_su.{f} IS NULL AND beltfish_obs.{f} IS NULL))"
        for f in su_fields
    ])

    sql = """
CREATE OR REPLACE VIEW public.vw_beltfish_su
 AS
SELECT NULL AS id,
{su_fields_su},
{agg_su_fields},
label, 
transect_width_name, 
reef_slope, 
size_bin, 
beltfish_tg.biomass_kgha,
beltfish_tg.biomass_kgha_by_trophic_group

FROM (
    SELECT {su_fields_obs},
    string_agg(DISTINCT label::text, ', '::text ORDER BY (label::text)) AS label,
    string_agg(DISTINCT relative_depth::text, ', '::text ORDER BY (relative_depth::text)) AS relative_depth,
    string_agg(DISTINCT sample_time::text, ', '::text ORDER BY (sample_time::text)) AS sample_time,
    string_agg(DISTINCT transect_width_name::text, ', '::text ORDER BY (transect_width_name::text)) AS 
    transect_width_name,
    string_agg(DISTINCT reef_slope::text, ', '::text ORDER BY (reef_slope::text)) AS reef_slope,
    string_agg(DISTINCT size_bin::text, ', '::text ORDER BY (size_bin::text)) AS size_bin,
    string_agg(DISTINCT current_name::text, ', '::text ORDER BY (current_name::text)) AS current_name,
    string_agg(DISTINCT tide_name::text, ', '::text ORDER BY (tide_name::text)) AS tide_name,
    string_agg(DISTINCT visibility_name::text, ', '::text ORDER BY (visibility_name::text)) AS visibility_name

    FROM vw_beltfish_obs
    GROUP BY {su_fields_obs}
) beltfish_su

INNER JOIN (
    SELECT {su_fields_tg},
    SUM(beltfish_obs_tg.biomass_kgha) AS biomass_kgha,
    jsonb_object_agg(
    CASE
        WHEN beltfish_obs_tg.trophic_group IS NULL THEN 'other'::character varying
        ELSE beltfish_obs_tg.trophic_group
    END, round(beltfish_obs_tg.biomass_kgha, 2)) AS biomass_kgha_by_trophic_group

    FROM (
        SELECT {su_fields_obs}, 
        COALESCE(sum(vw_beltfish_obs.biomass_kgha), 0::numeric) AS biomass_kgha,
        vw_beltfish_obs.trophic_group

        FROM vw_beltfish_obs
        GROUP BY {su_fields_obs}, 
        vw_beltfish_obs.trophic_group
    ) beltfish_obs_tg
    GROUP BY {su_fields_tg}
) beltfish_tg
ON {su_tg_join}

INNER JOIN (
    SELECT {su_fields_obs_obs},
    jsonb_agg(DISTINCT observer) AS observers

    FROM (
        SELECT {su_fields_obs},
        jsonb_array_elements(observers) AS observer
        
        FROM vw_beltfish_obs
        GROUP BY {su_fields_obs}, 
        vw_beltfish_obs.observers
    ) beltfish_obs_obs
    GROUP BY {su_fields_obs_obs}
) beltfish_obs
ON {su_obs_join}
    """.format(
        su_fields_su=", ".join([f"beltfish_su.{f}" for f in su_fields]),
        agg_su_fields=", ".join(BaseSUViewModel.agg_su_fields),
        su_fields_obs=", ".join([f"vw_beltfish_obs.{f}" for f in su_fields]),
        su_fields_obs_obs=", ".join([f"beltfish_obs_obs.{f}" for f in su_fields]),
        su_fields_tg=", ".join([f"beltfish_obs_tg.{f}" for f in su_fields]),
        su_tg_join=su_tg_join,
        su_obs_join=su_obs_join,
    )

    reverse_sql = "DROP VIEW IF EXISTS public.vw_beltfish_su CASCADE;"

    transect_number = models.PositiveSmallIntegerField()
    label = models.CharField(max_length=50, blank=True)
    transect_len_surveyed = models.PositiveSmallIntegerField(
        verbose_name=_("transect length surveyed (m)")
    )
    transect_width_name = models.CharField(max_length=100, null=True, blank=True)
    reef_slope = models.CharField(max_length=50)
    size_bin = models.PositiveSmallIntegerField()
    biomass_kgha = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name=_("biomass (kg/ha)"),
        null=True,
        blank=True,
    )
    biomass_kgha_by_trophic_group = JSONField(null=True, blank=True)
    data_policy_beltfish = models.CharField(max_length=50)

    objects = ExtendedManager()

    class Meta:
        db_table = "vw_beltfish_su"
        managed = False


class BeltFishSEView(BaseViewModel):
    project_lookup = "project_id"

    sql = """
CREATE OR REPLACE VIEW public.vw_beltfish_se
 AS
-- For each SE, summarize biomass by 1) avg of transects and 2) avg of transects' trophic groups
SELECT vw_beltfish_su.sample_event_id AS id,
{se_fields},
data_policy_beltfish, 

string_agg(DISTINCT current_name, ', ' ORDER BY current_name) AS current_name,
string_agg(DISTINCT tide_name, ', ' ORDER BY tide_name) AS tide_name,
string_agg(DISTINCT visibility_name, ', ' ORDER BY visibility_name) AS visibility_name,
COUNT(vw_beltfish_su.id) AS sample_unit_count,
ROUND(AVG("depth"), 2) as depth_avg,
biomass_kgha_avg,
biomass_kgha_by_trophic_group_avg

FROM vw_beltfish_su

INNER JOIN (
    SELECT meta_sus.sample_event_id, 
    ROUND(AVG(meta_sus.biomass_kgha), 2) AS biomass_kgha_avg
    FROM (
        SELECT sample_event_id, 
        SUM(biomass_kgha) AS biomass_kgha
        FROM vw_beltfish_su
        GROUP BY sample_event_id
    ) meta_sus
    GROUP BY meta_sus.sample_event_id
) AS beltfish_se 
ON vw_beltfish_su.sample_event_id = beltfish_se.sample_event_id

INNER JOIN (
    SELECT sample_event_id,
    jsonb_object_agg(tg, ROUND(biomass_kgha::numeric, 2)) AS biomass_kgha_by_trophic_group_avg
    FROM (
        SELECT meta_su_tgs.sample_event_id, tg,
        AVG(biomass_kgha) AS biomass_kgha
        FROM (
            SELECT sample_event_id, transect_number, depth, tgdata.key AS tg,
            SUM(tgdata.value::double precision) AS biomass_kgha
            FROM vw_beltfish_su,
            LATERAL jsonb_each_text(biomass_kgha_by_trophic_group) tgdata(key, value)
            GROUP BY sample_event_id, transect_number, depth, tgdata.key
        ) meta_su_tgs
        GROUP BY meta_su_tgs.sample_event_id, tg
    ) beltfish_su_tg
    GROUP BY sample_event_id
) AS beltfish_se_tg
ON vw_beltfish_su.sample_event_id = beltfish_se_tg.sample_event_id

GROUP BY 
{se_fields},
data_policy_beltfish,
biomass_kgha_avg,
biomass_kgha_by_trophic_group_avg;
    """.format(
        se_fields=", ".join([f"vw_beltfish_su.{f}" for f in BaseViewModel.se_fields]),
    )

    reverse_sql = "DROP VIEW IF EXISTS public.vw_beltfish_se CASCADE;"

    sample_unit_count = models.PositiveSmallIntegerField()
    depth_avg = models.DecimalField(
        max_digits=4, decimal_places=2, verbose_name=_("depth (m)")
    )
    biomass_kgha_avg = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name=_("biomass (kg/ha)"),
        null=True,
        blank=True,
    )
    biomass_kgha_by_trophic_group_avg = JSONField(null=True, blank=True)
    data_policy_beltfish = models.CharField(max_length=50)

    objects = ExtendedManager()

    class Meta:
        db_table = "vw_beltfish_se"
        managed = False
