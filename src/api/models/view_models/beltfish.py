from django.utils.translation import ugettext_lazy as _
from ..base import ExtendedManager
from .base import *


class BeltFishObsView(BaseViewModel):
    sql = """
{sample_event_view}

CREATE OR REPLACE VIEW public.vw_beltfish_obs
 AS
 SELECT 
    o.id,
    {se_fields},
    se.sample_event_id, 
    se.current_name,
    se.tide_name, 
    se.visibility_name, 
    se.sample_time, 
    se.sample_event_notes, 
    se.data_policy_beltfish,
    observers.observers, 
    tt.transectmethod_ptr_id AS sample_unit_id,
    tbf.number AS transect_number,
    tbf.label,
    tbf.len_surveyed AS transect_len_surveyed,
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
        (tbf.len_surveyed * wc.val)::numeric, 
        2
    )::numeric AS biomass_kgha,
    o.notes AS observation_notes
   FROM obs_transectbeltfish o
     JOIN vw_fish_attributes f ON o.fish_attribute_id = f.id
     RIGHT JOIN transectmethod_transectbeltfish tt ON o.beltfish_id = tt.transectmethod_ptr_id
     JOIN transect_belt_fish tbf ON tt.transect_id = tbf.id
     LEFT JOIN api_fishsizebin sb ON tbf.size_bin_id = sb.id
     LEFT JOIN api_reefslope rs ON tbf.reef_slope_id = rs.id
     JOIN api_belttransectwidth w ON tbf.width_id = w.id
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
          GROUP BY tt_1.transect_id) observers ON tbf.id = observers.transect_id
     JOIN vw_sample_events se ON tbf.sample_event_id = se.sample_event_id;
    """.format(
        sample_event_view=SampleEventViewModel.sql,
        se_fields=", ".join([f"se.{f}" for f in BaseViewModel.se_fields]),
    )

    sample_event_id = models.UUIDField()
    sample_event_notes = models.TextField(blank=True)
    sample_unit_id = models.UUIDField()
    sample_time = models.TimeField()
    observers = JSONField(null=True, blank=True)
    transect_number = models.PositiveSmallIntegerField()
    label = models.CharField(max_length=50, blank=True)
    transect_len_surveyed = models.PositiveSmallIntegerField(
        verbose_name=_("transect length surveyed (m)")
    )
    transect_width_name = models.CharField(max_length=100, null=True, blank=True)
    depth = models.DecimalField(
        max_digits=3, decimal_places=1, verbose_name=_("depth (m)")
    )
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
    size_bin = models.PositiveSmallIntegerField(null=True, blank=True)
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


class BeltFishSUView(BaseViewModel):
    project_lookup = "project_id"

    # NOT grouping by sample_time
    sql = """
CREATE OR REPLACE VIEW public.vw_beltfish_su
 AS
SELECT 
id, {se_fields},
current_name, tide_name, visibility_name, 
transect_number, transect_len_surveyed, transect_width_name, observers, 
reef_slope, size_bin, data_policy_beltfish, 

SUM(biomass_kgha) AS biomass_kgha,
jsonb_object_agg(
    (CASE WHEN trophic_group IS NULL THEN 'other' ELSE trophic_group END), 
    ROUND(biomass_kgha, 2)
) AS biomass_kgha_by_trophic_group
 
FROM (
    SELECT sample_unit_id AS id, {se_fields},
    string_agg(DISTINCT current_name, ', ' ORDER BY current_name) AS current_name,
    string_agg(DISTINCT tide_name, ', ' ORDER BY tide_name) AS tide_name,
    string_agg(DISTINCT visibility_name, ', ' ORDER BY visibility_name) AS visibility_name,
    transect_number, transect_len_surveyed, transect_width_name, observers,  
    reef_slope, size_bin, data_policy_beltfish, 
    trophic_group, 

    COALESCE(SUM(biomass_kgha), 0) AS biomass_kgha
    
    FROM vw_beltfish_obs
    GROUP BY sample_unit_id, 
    {se_fields},  
    transect_number, transect_len_surveyed, transect_width_name, observers,  
    reef_slope, size_bin, data_policy_beltfish, 
    trophic_group
) AS beltfish_obs_tg

GROUP BY id, {se_fields}, 
current_name, tide_name, visibility_name, 
transect_number, transect_len_surveyed, transect_width_name, observers,  
reef_slope, size_bin, data_policy_beltfish
    """.format(
        se_fields=", ".join(BaseViewModel.se_fields)
    )

    observers = JSONField(null=True, blank=True)
    transect_number = models.PositiveSmallIntegerField()
    transect_len_surveyed = models.PositiveSmallIntegerField(
        verbose_name=_("transect length surveyed (m)")
    )
    transect_width_name = models.CharField(max_length=100, null=True, blank=True)
    depth = models.DecimalField(
        max_digits=3, decimal_places=1, verbose_name=_("depth (m)")
    )
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
WITH meta_sus AS (
    SELECT project_id, site_id, management_id, sample_date,
    SUM(biomass_kgha) AS biomass_kgha
    FROM vw_beltfish_su
    GROUP BY project_id, site_id, management_id, sample_date, transect_number, depth
),
meta_su_tgs AS (
    SELECT project_id, site_id, management_id, sample_date, transect_number, depth,
    tgdata.key AS tg,
    SUM(tgdata.value::double precision) AS biomass_kgha
    FROM vw_beltfish_su,
    LATERAL jsonb_each_text(biomass_kgha_by_trophic_group) tgdata(key, value)
    GROUP BY project_id, site_id, management_id, sample_date, transect_number, depth, tgdata.key
)

SELECT 
NULL AS id,
vw_beltfish_su.project_id, project_name, project_status, project_notes, contact_link, tags, 
vw_beltfish_su.site_id, site_name, "location", site_notes, 
country_id, country_name, 
reef_type, reef_zone, reef_exposure, 
vw_beltfish_su.management_id, management_name, management_name_secondary, management_est_year, management_size, 
management_parties, management_compliance, management_rules, management_notes, 
string_agg(DISTINCT current_name, ', ' ORDER BY current_name) AS current_name,
string_agg(DISTINCT tide_name, ', ' ORDER BY tide_name) AS tide_name,
string_agg(DISTINCT visibility_name, ', ' ORDER BY visibility_name) AS visibility_name,
vw_beltfish_su.sample_date, data_policy_beltfish, 
COUNT(vw_beltfish_su.id) AS sample_unit_count,
ROUND(AVG("depth"), 2) as depth_avg,
biomass_kgha_avg,
biomass_kgha_by_trophic_group_avg

FROM public.vw_beltfish_su

INNER JOIN (
    SELECT meta_sus.project_id, meta_sus.site_id, meta_sus.management_id, meta_sus.sample_date,
    ROUND(AVG(meta_sus.biomass_kgha), 2) AS biomass_kgha_avg
    FROM meta_sus
    GROUP BY meta_sus.project_id, meta_sus.site_id, meta_sus.management_id, meta_sus.sample_date
) AS beltfish_se 
ON (
    vw_beltfish_su.project_id = beltfish_se.project_id
    AND vw_beltfish_su.site_id = beltfish_se.site_id
    AND vw_beltfish_su.management_id = beltfish_se.management_id
    AND vw_beltfish_su.sample_date = beltfish_se.sample_date
)

INNER JOIN (
    SELECT project_id, site_id, management_id, sample_date,
    jsonb_object_agg(tg, ROUND(biomass_kgha::numeric, 2)) AS biomass_kgha_by_trophic_group_avg
    FROM (
        SELECT meta_su_tgs.project_id, meta_su_tgs.site_id, meta_su_tgs.management_id, meta_su_tgs.sample_date,
        tg,
        AVG(biomass_kgha) AS biomass_kgha
        FROM meta_su_tgs
        GROUP BY meta_su_tgs.project_id, meta_su_tgs.site_id, meta_su_tgs.management_id, meta_su_tgs.sample_date,
        tg
    ) beltfish_su_tg
    GROUP BY project_id, site_id, management_id, sample_date
) AS beltfish_se_tg
ON (
    vw_beltfish_su.project_id = beltfish_se_tg.project_id
    AND vw_beltfish_su.site_id = beltfish_se_tg.site_id
    AND vw_beltfish_su.management_id = beltfish_se_tg.management_id
    AND vw_beltfish_su.sample_date = beltfish_se_tg.sample_date
)

GROUP BY 
vw_beltfish_su.project_id, project_name, project_status, project_notes, contact_link, tags, 
vw_beltfish_su.site_id, site_name, "location", site_notes, 
country_id, country_name, 
reef_type, reef_zone, reef_exposure, 
vw_beltfish_su.management_id, management_name, management_name_secondary, management_est_year, management_size, 
management_parties, management_compliance, management_rules, management_notes, 
vw_beltfish_su.sample_date, data_policy_beltfish,
biomass_kgha_avg,
biomass_kgha_by_trophic_group_avg;
    """

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
