from django.utils.translation import ugettext_lazy as _
from .base import *


class SummarySiteViewModel(models.Model):
    sql = """
CREATE MATERIALIZED VIEW IF NOT EXISTS vw_summary_site AS 
SELECT 
site.id AS site_id, 
site.name AS site_name, 
site.location,
site.notes AS site_notes,
project.id AS project_id, 
project.name AS project_name, 
project.status AS project_status,
project.notes AS project_notes,
'https://datamermaid.org/contact-project/?project_id=' || COALESCE(project.id::text, '') AS contact_link,
country.id AS country_id,
country.name AS country_name,
api_reeftype.name AS reef_type,
api_reefzone.name AS reef_zone,
api_reefexposure.name AS reef_exposure,
tags.tags,
pa.project_admins,
se.date_min,
se.date_max,
se.depth_avg_min,
se.depth_avg_max,
mrs.management_regimes,
(CASE WHEN project.data_policy_beltfish=10 THEN 'private'
    WHEN project.data_policy_beltfish=50 THEN 'public summary'
    WHEN project.data_policy_beltfish=100 THEN 'public'
    ELSE ''
END) AS data_policy_beltfish, 
(CASE WHEN project.data_policy_benthiclit=10 THEN 'private'
    WHEN project.data_policy_benthiclit=50 THEN 'public summary'
    WHEN project.data_policy_benthiclit=100 THEN 'public'
    ELSE ''
END) AS data_policy_benthiclit, 
(CASE WHEN project.data_policy_benthicpit=10 THEN 'private'
    WHEN project.data_policy_benthicpit=50 THEN 'public summary'
    WHEN project.data_policy_benthicpit=100 THEN 'public'
    ELSE ''
END) AS data_policy_benthicpit, 
(CASE WHEN project.data_policy_habitatcomplexity=10 THEN 'private'
    WHEN project.data_policy_habitatcomplexity=50 THEN 'public summary'
    WHEN project.data_policy_habitatcomplexity=100 THEN 'public'
    ELSE ''
END) AS data_policy_habitatcomplexity, 
(CASE WHEN project.data_policy_bleachingqc=10 THEN 'private'
    WHEN project.data_policy_bleachingqc=50 THEN 'public summary'
    WHEN project.data_policy_bleachingqc=100 THEN 'public'
    ELSE ''
END) AS data_policy_bleachingqc, 

jsonb_strip_nulls(jsonb_build_object(
    'beltfish', NULLIF(jsonb_strip_nulls(jsonb_build_object(
        'sample_unit_count', fb.sample_unit_count,
        'biomass_kgha_avg', (CASE WHEN project.data_policy_beltfish < 50 THEN NULL ELSE fb.biomass_kgha_avg END),  
        'biomass_kgha_by_trophic_group_avg', (CASE WHEN project.data_policy_beltfish < 50 THEN NULL ELSE 
        fbtg.biomass_kgha_by_trophic_group_avg END)
    )), '{}'),
    'benthiclit', NULLIF(jsonb_strip_nulls(jsonb_build_object(
        'sample_unit_count', bl.sample_unit_count,
        'percent_cover_by_benthic_category_avg', (CASE WHEN project.data_policy_benthiclit < 50 THEN NULL ELSE 
        bl.percent_cover_by_benthic_category_avg END)
    )), '{}'),
    'benthicpit', NULLIF(jsonb_strip_nulls(jsonb_build_object(
        'sample_unit_count', bp.sample_unit_count,
        'percent_cover_by_benthic_category_avg', (CASE WHEN project.data_policy_benthicpit < 50 THEN NULL ELSE 
        bp.percent_cover_by_benthic_category_avg END)
    )), '{}'),
    'habitatcomplexity', NULLIF(jsonb_strip_nulls(jsonb_build_object(
        'sample_unit_count', hc.sample_unit_count,
        'score_avg_avg', (CASE WHEN project.data_policy_habitatcomplexity < 50 THEN NULL ELSE hc.score_avg_avg END)
    )), '{}'),
    'colonies_bleached', NULLIF(jsonb_strip_nulls(jsonb_build_object(
        'sample_unit_count', bleachingqc.sample_unit_count,
        'count_total_avg', (CASE WHEN project.data_policy_bleachingqc < 50 THEN NULL ELSE bleachingqc.count_total_avg 
        END),
        'count_genera_avg', (CASE WHEN project.data_policy_bleachingqc < 50 THEN NULL ELSE 
        bleachingqc.count_genera_avg END),
        'percent_normal_avg', (CASE WHEN project.data_policy_bleachingqc < 50 THEN NULL ELSE 
        bleachingqc.percent_normal_avg END),
        'percent_pale_avg', (CASE WHEN project.data_policy_bleachingqc < 50 THEN NULL ELSE 
        bleachingqc.percent_pale_avg END),
        'percent_bleached_avg', (CASE WHEN project.data_policy_bleachingqc < 50 THEN NULL ELSE 
        bleachingqc.percent_bleached_avg END)
    )), '{}'),
    'quadrat_benthic_percent', NULLIF(jsonb_strip_nulls(jsonb_build_object(
        'sample_unit_count', bleachingqc.sample_unit_count,
        'percent_hard_avg_avg', (CASE WHEN project.data_policy_bleachingqc < 50 THEN NULL ELSE 
        bleachingqc.percent_hard_avg_avg END),
        'percent_soft_avg_avg', (CASE WHEN project.data_policy_bleachingqc < 50 THEN NULL ELSE 
        bleachingqc.percent_soft_avg_avg END),
        'percent_algae_avg_avg', (CASE WHEN project.data_policy_bleachingqc < 50 THEN NULL ELSE 
        bleachingqc.percent_algae_avg_avg END),
        'quadrat_count_avg', (CASE WHEN project.data_policy_bleachingqc < 50 THEN NULL ELSE 
        bleachingqc.quadrat_count_avg END)
    )), '{}')
)) AS protocols

FROM site
INNER JOIN project ON (site.project_id = project.id)
INNER JOIN country ON (site.country_id = country.id)
INNER JOIN api_reeftype ON (site.reef_type_id = api_reeftype.id)
INNER JOIN api_reefzone ON (site.reef_zone_id = api_reefzone.id)
INNER JOIN api_reefexposure ON (site.exposure_id = api_reefexposure.id)

INNER JOIN (
    SELECT project.id, 
    jsonb_agg(
        jsonb_build_object('name', COALESCE(profile.first_name, '') || ' ' || COALESCE(profile.last_name, ''))
    ) AS project_admins
    FROM project
    INNER JOIN project_profile ON (project.id = project_profile.project_id)
    INNER JOIN profile ON (project_profile.profile_id = profile.id)
    WHERE project_profile.role >= 90
    GROUP BY project.id
) pa ON (project.id = pa.id)

LEFT JOIN (
    SELECT project.id, 
    jsonb_agg(
        jsonb_build_object('id', t.id, 'name', t.name)
    ) AS tags
    FROM api_uuidtaggeditem ti
    INNER JOIN django_content_type ct ON (ti.content_type_id = ct.id)
    INNER JOIN project ON (ti.object_id = project.id)
    INNER JOIN api_tag t ON (ti.tag_id = t.id)
    WHERE ct.app_label = 'api' AND ct.model = 'project'
    GROUP BY project.id
) tags ON (project.id = tags.id)

LEFT JOIN (
    SELECT site_id, 
    MIN(depth) AS depth_avg_min,
    MAX(depth) AS depth_avg_max,
    MIN(sample_date) AS date_min,
    MAX(sample_date) AS date_max
    FROM sample_event
    GROUP BY site_id
) se ON (site.id = se.site_id)

LEFT JOIN (
    SELECT site_id, 
    jsonb_agg(DISTINCT jsonb_strip_nulls(jsonb_build_object(
        'id', management_id,
        'name', CASE WHEN m.name_secondary = '' THEN m.name ELSE m.name || ' [' || m.name_secondary || ']' END,
        'notes', NULLIF(m.notes, '')
    ))) AS management_regimes
    FROM sample_event s
    INNER JOIN management m ON (s.management_id = m.id)
    GROUP BY site_id
) mrs ON (site.id = mrs.site_id)

LEFT JOIN (
    SELECT site_id,
    COUNT(pseudosu_id) AS sample_unit_count,
    ROUND(AVG(biomass_kgha), 1) AS biomass_kgha_avg
    FROM vw_beltfish_su
    GROUP BY site_id
) fb ON (site.id = fb.site_id)
LEFT JOIN (
    SELECT site_id,
    jsonb_object_agg(tg, ROUND(biomass_kgha::numeric, 2)) AS biomass_kgha_by_trophic_group_avg
    FROM (
        SELECT meta_su_tgs.site_id, tg,
        AVG(biomass_kgha) AS biomass_kgha
        FROM (
            SELECT site_id, pseudosu_id, tgdata.key AS tg,
            SUM(tgdata.value::double precision) AS biomass_kgha
            FROM vw_beltfish_su,
            LATERAL jsonb_each_text(biomass_kgha_by_trophic_group) tgdata(key, value)
            GROUP BY site_id, pseudosu_id, tgdata.key
        ) meta_su_tgs
        GROUP BY meta_su_tgs.site_id, tg
    ) beltfish_su_tg
    GROUP BY site_id
) fbtg ON (site.id = fbtg.site_id)

LEFT JOIN (
    SELECT vw_benthiclit_su.site_id,
    COUNT(pseudosu_id) AS sample_unit_count,
    percent_cover_by_benthic_category_avg
    FROM vw_benthiclit_su
    INNER JOIN (
        SELECT site_id, 
        jsonb_object_agg(cat, ROUND(cat_percent::numeric, 2)) AS percent_cover_by_benthic_category_avg
        FROM (
            SELECT site_id, 
            cpdata.key AS cat, 
            AVG(cpdata.value::float) AS cat_percent
            FROM vw_benthiclit_su,
            jsonb_each_text(percent_cover_by_benthic_category) AS cpdata
            GROUP BY site_id, cpdata.key
        ) AS benthiclit_su_cp
        GROUP BY site_id
    ) AS benthiclit_site_cat_percents
    ON vw_benthiclit_su.site_id = benthiclit_site_cat_percents.site_id
    GROUP BY 
    vw_benthiclit_su.site_id,
    percent_cover_by_benthic_category_avg
) bl ON (site.id = bl.site_id)

LEFT JOIN (
    SELECT vw_benthicpit_su.site_id,
    COUNT(pseudosu_id) AS sample_unit_count,
    percent_cover_by_benthic_category_avg
    FROM vw_benthicpit_su
    INNER JOIN (
        SELECT site_id, 
        jsonb_object_agg(cat, ROUND(cat_percent::numeric, 2)) AS percent_cover_by_benthic_category_avg
        FROM (
            SELECT site_id, 
            cpdata.key AS cat, 
            AVG(cpdata.value::float) AS cat_percent
            FROM vw_benthicpit_su,
            jsonb_each_text(percent_cover_by_benthic_category) AS cpdata
            GROUP BY site_id, cpdata.key
        ) AS benthicpit_su_cp
        GROUP BY site_id
    ) AS benthicpit_site_cat_percents
    ON vw_benthicpit_su.site_id = benthicpit_site_cat_percents.site_id
    GROUP BY 
    vw_benthicpit_su.site_id,
    percent_cover_by_benthic_category_avg
) bp ON (site.id = bp.site_id)

LEFT JOIN (
    SELECT site_id,
    COUNT(pseudosu_id) AS sample_unit_count,
    ROUND(AVG(score_avg), 2) AS score_avg_avg
    FROM vw_habitatcomplexity_su
    GROUP BY 
    site_id
) hc ON (site.id = hc.site_id)

LEFT JOIN (
    SELECT site_id, 
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
    FROM vw_bleachingqc_su
    GROUP BY 
    site_id
) bleachingqc ON (site.id = bleachingqc.site_id);

CREATE UNIQUE INDEX ON vw_summary_site (site_id);
    """

    reverse_sql = "DROP MATERIALIZED VIEW IF EXISTS vw_summary_site CASCADE;"

    site_id = models.UUIDField(primary_key=True)
    site_name = models.CharField(max_length=255)
    site_notes = models.TextField(blank=True)
    location = models.PointField(srid=4326)
    project_id = models.UUIDField()
    project_name = models.CharField(max_length=255)
    project_status = models.PositiveSmallIntegerField(
        choices=Project.STATUSES, default=Project.OPEN
    )
    project_notes = models.TextField(blank=True)
    contact_link = models.CharField(max_length=255)
    tags = JSONField(null=True, blank=True)
    country_id = models.UUIDField()
    country_name = models.CharField(max_length=50)
    reef_type = models.CharField(max_length=50)
    reef_zone = models.CharField(max_length=50)
    reef_exposure = models.CharField(max_length=50)  # name change
    project_admins = JSONField(null=True, blank=True)
    date_min = models.DateField(null=True, blank=True)
    date_max = models.DateField(null=True, blank=True)
    # depth avg min/max instead of single json field
    depth_avg_min = models.DecimalField(max_digits=3, decimal_places=1)
    depth_avg_max = models.DecimalField(max_digits=3, decimal_places=1)
    management_regimes = JSONField(null=True, blank=True)
    protocols = JSONField(null=True, blank=True)  # most keys changed inside here
    data_policy_beltfish = models.CharField(max_length=50)
    data_policy_benthiclit = models.CharField(max_length=50)
    data_policy_benthicpit = models.CharField(max_length=50)
    data_policy_habitatcomplexity = models.CharField(max_length=50)
    data_policy_bleachingqc = models.CharField(max_length=50)

    class Meta:
        db_table = "vw_summary_site"
        managed = False
