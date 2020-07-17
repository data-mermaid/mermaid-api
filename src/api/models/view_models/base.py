import uuid
from django.contrib.gis.db import models
from django.contrib.postgres.fields import JSONField
from django.utils.translation import ugettext_lazy as _
from ..mermaid import Project, FishAttribute


class FishAttributeView(FishAttribute):
    sql = """
CREATE OR REPLACE VIEW public.vw_fish_attributes
 AS
WITH fish_grouping_aggregates AS (
    WITH species_groupings AS (
        SELECT DISTINCT fish_species.fishattribute_ptr_id AS species_id,
        r.grouping_id,
        fish_grouping.name,
        biomass_constant_a, biomass_constant_b, biomass_constant_c,
        fish_group_trophic.name AS trophic_group_name,
        fish_group_function.name AS trophic_function_name,
        trophic_level, vulnerability
        FROM fish_species
        LEFT JOIN fish_group_trophic ON (fish_species.trophic_group_id = fish_group_trophic.id)
        LEFT JOIN fish_group_function ON (fish_species.functional_group_id = fish_group_function.id)
        INNER JOIN fish_genus ON (fish_species.genus_id = fish_genus.fishattribute_ptr_id) 
        INNER JOIN api_fishgroupingrelationship r ON (
            fish_species.fishattribute_ptr_id = r.attribute_id
            OR fish_species.genus_id = r.attribute_id
            OR fish_genus.family_id = r.attribute_id
        )
        INNER JOIN fish_species_regions sr ON (fish_species.fishattribute_ptr_id = sr.fishspecies_id) 
        INNER JOIN fish_grouping ON (r.grouping_id = fish_grouping.fishattribute_ptr_id)
        WHERE sr.region_id IN (
            SELECT region.id 
            FROM region 
            INNER JOIN fish_grouping_regions sr2 ON (region.id = sr2.region_id) 
            WHERE sr2.fishgrouping_id = fish_grouping.fishattribute_ptr_id
        )
    )
    SELECT species_groupings.grouping_id,
    species_groupings.name,
    AVG(biomass_constant_a) AS biomass_constant_a,
    AVG(biomass_constant_b) AS biomass_constant_b,
    AVG(biomass_constant_c) AS biomass_constant_c,
    tg_groupings.trophic_group_name,
    fg_groupings.trophic_function_name,
    AVG(trophic_level) AS trophic_level,
    AVG(vulnerability) AS vulnerability
    FROM species_groupings
    LEFT JOIN (
        SELECT grouping_id, trophic_group_name, cnt
        FROM (
            SELECT grouping_id, trophic_group_name, cnt,
            RANK() OVER (PARTITION BY grouping_id ORDER BY cnt DESC) AS rnk
            FROM (
                SELECT grouping_id, trophic_group_name, COUNT(*) AS cnt
                FROM species_groupings
                GROUP BY grouping_id, trophic_group_name
            ) AS tgg
        ) AS tg_groupings_ranked
        WHERE tg_groupings_ranked.rnk = 1
    ) AS tg_groupings ON (species_groupings.grouping_id = tg_groupings.grouping_id)
    LEFT JOIN (
        SELECT grouping_id, trophic_function_name, cnt
        FROM (
            SELECT grouping_id, trophic_function_name, cnt,
            RANK() OVER (PARTITION BY grouping_id ORDER BY cnt DESC) AS rnk
            FROM (
                SELECT grouping_id, trophic_function_name, COUNT(*) AS cnt
                FROM species_groupings
                GROUP BY grouping_id, trophic_function_name
            ) AS tfg
        ) AS fg_groupings_ranked
        WHERE fg_groupings_ranked.rnk = 1
    ) AS fg_groupings ON (species_groupings.grouping_id = fg_groupings.grouping_id)
    GROUP BY species_groupings.grouping_id, species_groupings.name, tg_groupings.trophic_group_name, 
    fg_groupings.trophic_function_name
)

SELECT fish_attribute.id,
fish_attribute.id AS fishattribute_ptr_id,
fish_attribute.created_on,
fish_attribute.updated_on,
fish_attribute.updated_by_id,
fish_attribute.status,
CASE
    WHEN fish_species.name IS NOT NULL THEN species_genus_family.name
    WHEN fish_genus.name IS NOT NULL THEN genus_family.name
    WHEN fish_family.name IS NOT NULL THEN fish_family.name::text
    ELSE NULL::text
END AS name_family,
CASE
    WHEN fish_species.name IS NOT NULL THEN species_genus.name
    WHEN fish_genus.name IS NOT NULL THEN fish_genus.name::text
    ELSE NULL::text
END AS name_genus,
CASE
    WHEN fish_species.name IS NOT NULL THEN concat(species_genus.name, ' ', fish_species.name)
    WHEN fish_genus.name IS NOT NULL THEN fish_genus.name::text
    WHEN fish_family.name IS NOT NULL THEN fish_family.name::text
    WHEN fish_grouping_aggregates.name IS NOT NULL THEN fish_grouping_aggregates.name::text
    ELSE NULL::text
END AS name,

CASE
    WHEN fish_species.biomass_constant_a IS NOT NULL THEN fish_species.biomass_constant_a
    WHEN fish_genus.name IS NOT NULL THEN round(( SELECT avg(fish_species_1.biomass_constant_a) AS avg
       FROM fish_species fish_species_1
      WHERE fish_species_1.genus_id = fish_attribute.id), 6)
    WHEN fish_family.name IS NOT NULL THEN round(( SELECT avg(fish_species_1.biomass_constant_a) AS avg
       FROM fish_species fish_species_1
         JOIN fish_genus fish_genus_1 ON fish_species_1.genus_id = fish_genus_1.fishattribute_ptr_id
      WHERE fish_genus_1.family_id = fish_attribute.id), 6)
    WHEN fish_grouping_aggregates.name IS NOT NULL THEN ROUND(fish_grouping_aggregates.biomass_constant_a, 6)
    ELSE NULL::numeric
END AS biomass_constant_a,

CASE
    WHEN fish_species.biomass_constant_b IS NOT NULL THEN fish_species.biomass_constant_b
    WHEN fish_genus.name IS NOT NULL THEN round(( SELECT avg(fish_species_1.biomass_constant_b) AS avg
       FROM fish_species fish_species_1
      WHERE fish_species_1.genus_id = fish_attribute.id), 6)
    WHEN fish_family.name IS NOT NULL THEN round(( SELECT avg(fish_species_1.biomass_constant_b) AS avg
       FROM fish_species fish_species_1
         JOIN fish_genus fish_genus_1 ON fish_species_1.genus_id = fish_genus_1.fishattribute_ptr_id
      WHERE fish_genus_1.family_id = fish_attribute.id), 6)
    WHEN fish_grouping_aggregates.name IS NOT NULL THEN ROUND(fish_grouping_aggregates.biomass_constant_b, 6)
    ELSE NULL::numeric
END AS biomass_constant_b,

CASE
    WHEN fish_species.biomass_constant_c IS NOT NULL THEN fish_species.biomass_constant_c
    WHEN fish_genus.name IS NOT NULL THEN round(( SELECT avg(fish_species_1.biomass_constant_c) AS avg
       FROM fish_species fish_species_1
      WHERE fish_species_1.genus_id = fish_attribute.id), 6)
    WHEN fish_family.name IS NOT NULL THEN round(( SELECT avg(fish_species_1.biomass_constant_c) AS avg
       FROM fish_species fish_species_1
         JOIN fish_genus fish_genus_1 ON fish_species_1.genus_id = fish_genus_1.fishattribute_ptr_id
      WHERE fish_genus_1.family_id = fish_attribute.id), 6)
    WHEN fish_grouping_aggregates.name IS NOT NULL THEN ROUND(fish_grouping_aggregates.biomass_constant_c, 6)
    ELSE NULL::numeric
END AS biomass_constant_c,

CASE
    WHEN fish_species.trophic_group_id IS NOT NULL THEN fish_group_trophic.name
    WHEN fish_genus.name IS NOT NULL THEN ( SELECT fgt.name
       FROM ( SELECT fish_group_trophic_1.name,
                count(*) AS freq
               FROM fish_species fish_species_1
                 JOIN fish_group_trophic fish_group_trophic_1 ON fish_species_1.trophic_group_id = 
                 fish_group_trophic_1.id
              WHERE fish_species_1.genus_id = fish_attribute.id
              GROUP BY fish_group_trophic_1.name
              ORDER BY (count(*)) DESC, fish_group_trophic_1.name
             LIMIT 1) fgt)
    WHEN fish_family.name IS NOT NULL THEN ( SELECT fft.name
       FROM ( SELECT fish_group_trophic_1.name,
                count(*) AS freq
               FROM fish_species fish_species_1
                 JOIN fish_group_trophic fish_group_trophic_1 ON fish_species_1.trophic_group_id = 
                 fish_group_trophic_1.id
                 JOIN fish_genus fish_genus_1 ON fish_species_1.genus_id = fish_genus_1.fishattribute_ptr_id
              WHERE fish_genus_1.family_id = fish_attribute.id
              GROUP BY fish_group_trophic_1.name
              ORDER BY (count(*)) DESC, fish_group_trophic_1.name
             LIMIT 1) fft)
    WHEN fish_grouping_aggregates.name IS NOT NULL THEN fish_grouping_aggregates.trophic_group_name
    ELSE NULL::character varying
END AS trophic_group,

CASE
    WHEN fish_species.functional_group_id IS NOT NULL THEN fish_group_function.name
    WHEN fish_genus.name IS NOT NULL THEN ( SELECT fgf.name
       FROM ( SELECT fish_group_function_1.name,
                count(*) AS freq
               FROM fish_species fish_species_1
                 JOIN fish_group_function fish_group_function_1 ON fish_species_1.functional_group_id = 
                 fish_group_function_1.id
              WHERE fish_species_1.genus_id = fish_attribute.id
              GROUP BY fish_group_function_1.name
              ORDER BY (count(*)) DESC, fish_group_function_1.name
             LIMIT 1) fgf)
    WHEN fish_family.name IS NOT NULL THEN ( SELECT fff.name
       FROM ( SELECT fish_group_function_1.name,
                count(*) AS freq
               FROM fish_species fish_species_1
                 JOIN fish_group_function fish_group_function_1 ON fish_species_1.functional_group_id = 
                 fish_group_function_1.id
                 JOIN fish_genus fish_genus_1 ON fish_species_1.genus_id = fish_genus_1.fishattribute_ptr_id
              WHERE fish_genus_1.family_id = fish_attribute.id
              GROUP BY fish_group_function_1.name
              ORDER BY (count(*)) DESC, fish_group_function_1.name
             LIMIT 1) fff)
    WHEN fish_grouping_aggregates.name IS NOT NULL THEN fish_grouping_aggregates.trophic_function_name
    ELSE NULL::character varying
END AS functional_group,

CASE
    WHEN fish_species.trophic_level IS NOT NULL THEN fish_species.trophic_level
    WHEN fish_genus.name IS NOT NULL THEN round(( SELECT avg(fish_species_1.trophic_level) AS avg
       FROM fish_species fish_species_1
      WHERE fish_species_1.genus_id = fish_attribute.id), 2)
    WHEN fish_family.name IS NOT NULL THEN round(( SELECT avg(fish_species_1.trophic_level) AS avg
       FROM fish_species fish_species_1
         JOIN fish_genus fish_genus_1 ON fish_species_1.genus_id = fish_genus_1.fishattribute_ptr_id
      WHERE fish_genus_1.family_id = fish_attribute.id), 2)
    WHEN fish_grouping_aggregates.name IS NOT NULL THEN ROUND(fish_grouping_aggregates.trophic_level, 2)
    ELSE NULL::numeric
END AS trophic_level,

CASE
    WHEN fish_species.vulnerability IS NOT NULL THEN fish_species.vulnerability
    WHEN fish_genus.name IS NOT NULL THEN round(( SELECT avg(fish_species_1.vulnerability) AS avg
       FROM fish_species fish_species_1
      WHERE fish_species_1.genus_id = fish_attribute.id), 2)
    WHEN fish_family.name IS NOT NULL THEN round(( SELECT avg(fish_species_1.vulnerability) AS avg
       FROM fish_species fish_species_1
         JOIN fish_genus fish_genus_1 ON fish_species_1.genus_id = fish_genus_1.fishattribute_ptr_id
      WHERE fish_genus_1.family_id = fish_attribute.id), 2)
    WHEN fish_grouping_aggregates.name IS NOT NULL THEN ROUND(fish_grouping_aggregates.vulnerability, 2)
    ELSE NULL::numeric
END AS vulnerability

FROM fish_attribute
LEFT JOIN fish_species ON fish_attribute.id = fish_species.fishattribute_ptr_id
LEFT JOIN fish_genus species_genus ON fish_species.genus_id = species_genus.fishattribute_ptr_id
LEFT JOIN fish_family species_genus_family ON species_genus.family_id = species_genus_family.fishattribute_ptr_id
LEFT JOIN fish_genus ON fish_attribute.id = fish_genus.fishattribute_ptr_id
LEFT JOIN fish_family genus_family ON fish_genus.family_id = genus_family.fishattribute_ptr_id
LEFT JOIN fish_family ON fish_attribute.id = fish_family.fishattribute_ptr_id
LEFT JOIN fish_grouping_aggregates ON (fish_attribute.id = fish_grouping_aggregates.grouping_id)
LEFT JOIN fish_group_trophic ON fish_species.trophic_group_id = fish_group_trophic.id
LEFT JOIN fish_group_function ON fish_species.functional_group_id = fish_group_function.id

ORDER BY (
    CASE
        WHEN fish_species.name IS NOT NULL THEN concat(species_genus.name, ' ', fish_species.name)
        WHEN fish_genus.name IS NOT NULL THEN fish_genus.name::text
        WHEN fish_family.name IS NOT NULL THEN fish_family.name::text
        WHEN fish_grouping_aggregates.name IS NOT NULL THEN fish_grouping_aggregates.name::text
        ELSE NULL::text
    END);

DROP MATERIALIZED VIEW IF EXISTS vw_summary_site;

CREATE MATERIALIZED VIEW IF NOT EXISTS vw_summary_site AS 

WITH fb_se_trophic_groups AS (
    SELECT 
    sample_event.site_id,
    sample_event.management_id,
    sample_event.sample_date,
    transect_belt_fish.number,
    f.trophic_group,
    SUM(
        10000 * -- m2 to ha: * here instead of / in denominator to avoid divide by 0 errors
        -- mass (kg)
        (o.count * f.biomass_constant_a * ((o.size * f.biomass_constant_c) ^ f.biomass_constant_b) / 1000)
        / (transect_belt_fish.len_surveyed * w.val) -- area (m2)
    ) AS biomass_kgha
    FROM obs_transectbeltfish o
    JOIN vw_fish_attributes f ON o.fish_attribute_id = f.id
    INNER JOIN transectmethod_transectbeltfish t ON (o.beltfish_id = t.transectmethod_ptr_id)
    INNER JOIN transect_belt_fish ON (t.transect_id = transect_belt_fish.id)
    INNER JOIN sample_event ON transect_belt_fish.sample_event_id = sample_event.id
    INNER JOIN api_belttransectwidth w ON (transect_belt_fish.width_id = w.id)
    GROUP BY sample_event.site_id, sample_event.management_id, sample_event.sample_date, transect_belt_fish.number, 
    f.trophic_group
)

SELECT site.id AS site_id, site.name AS site_name, 
ST_Y(site.location) AS lat, ST_X(site.location) AS lon,
site.notes AS site_notes,
project.id AS project_id, project.name AS project_name, 
project.status AS project_status,
project.notes AS project_notes,

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

'https://datamermaid.org/contact-project/?project_id=' || COALESCE(project.id::text, '') AS contact_link,
country.id AS country_id,
country.name AS country_name,
tags.tags,
pa.project_admins,
api_reeftype.name AS reef_type,
api_reefzone.name AS reef_zone,
api_reefexposure.name AS exposure,
sample_events.date_min,
sample_events.date_max,
sample_events.depth,
mrs.management_regimes,
jsonb_strip_nulls(jsonb_build_object(
    'beltfish', NULLIF(jsonb_strip_nulls(jsonb_build_object(
        'sample_unit_count', fb.sample_unit_count,
        'biomass_kgha', (CASE WHEN project.data_policy_beltfish < 50 THEN NULL ELSE fb.biomass_kgha END),
        'biomass_kgha_tg', (CASE WHEN project.data_policy_beltfish < 50 THEN NULL ELSE fb.biomass_kgha_tg END)
    )), '{}'),
    'benthiclit', NULLIF(jsonb_strip_nulls(jsonb_build_object(
        'sample_unit_count', bl.sample_unit_count,
        'coral_cover', (CASE WHEN project.data_policy_benthiclit < 50 THEN NULL ELSE bl.percent_avgs END)
    )), '{}'),
    'benthicpit', NULLIF(jsonb_strip_nulls(jsonb_build_object(
        'sample_unit_count', bp.sample_unit_count,
        'coral_cover', (CASE WHEN project.data_policy_benthicpit < 50 THEN NULL ELSE bp.percent_avgs END)
    )), '{}'),
    'habitatcomplexity', NULLIF(jsonb_strip_nulls(jsonb_build_object(
        'sample_unit_count', hc.sample_unit_count,
        'score_avg', (CASE WHEN project.data_policy_habitatcomplexity < 50 THEN NULL ELSE hc.score_avg END)
    )), '{}'),
    'colonies_bleached', NULLIF(jsonb_strip_nulls(jsonb_build_object(
        'sample_unit_count', qccb.sample_unit_count,
        'avg_count_total', (CASE WHEN project.data_policy_bleachingqc < 50 THEN NULL ELSE qccb.avg_count_total END),
        'avg_count_genera', (CASE WHEN project.data_policy_bleachingqc < 50 THEN NULL ELSE qccb.avg_count_genera END),
        'avg_percent_normal', (CASE WHEN project.data_policy_bleachingqc < 50 THEN NULL ELSE qccb.avg_percent_normal 
        END),
        'avg_percent_pale', (CASE WHEN project.data_policy_bleachingqc < 50 THEN NULL ELSE qccb.avg_percent_pale END),
        'avg_percent_bleached', (CASE WHEN project.data_policy_bleachingqc < 50 THEN NULL ELSE 
        qccb.avg_percent_bleached END)
    )), '{}'),
    'quadrat_benthic_percent', NULLIF(jsonb_strip_nulls(jsonb_build_object(
        'sample_unit_count', qcbp.sample_unit_count,
        'avg_percent_hard', (CASE WHEN project.data_policy_bleachingqc < 50 THEN NULL ELSE qcbp.avg_percent_hard END),
        'avg_percent_soft', (CASE WHEN project.data_policy_bleachingqc < 50 THEN NULL ELSE qcbp.avg_percent_soft END),
        'avg_percent_algae', (CASE WHEN project.data_policy_bleachingqc < 50 THEN NULL ELSE qcbp.avg_percent_algae END),
        'avg_quadrat_count', (CASE WHEN project.data_policy_bleachingqc < 50 THEN NULL ELSE qcbp.avg_quadrat_count END)
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
    jsonb_build_object(
        'min', MIN(depth),
        'max', MAX(depth)
    ) AS depth,
    MIN(sample_date) AS date_min,
    MAX(sample_date) AS date_max
    FROM sample_event
    GROUP BY site_id
) sample_events ON (site.id = sample_events.site_id)

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
    SELECT site_sus.site_id, sample_unit_count, site_sus.biomass_kgha, biomass_kgha_tg
    FROM (
        SELECT site_id, COUNT(sus.*) AS sample_unit_count, ROUND(SUM(biomass_kgha), 1) AS biomass_kgha
        FROM (
            SELECT site_id, management_id, sample_date, number, AVG(biomass_kgha) AS biomass_kgha
            FROM fb_se_trophic_groups
            -- field definition of sample event
            GROUP BY site_id, management_id, sample_date, number
            ORDER BY site_id
        ) AS sus
        GROUP BY site_id
    ) AS site_sus
    INNER JOIN (
        SELECT site_id, 
        jsonb_agg(
            jsonb_build_object((CASE WHEN trophic_group IS NULL THEN 'other' ELSE trophic_group END), 
            ROUND(biomass_kgha_tg, 3))
        ) AS biomass_kgha_tg
        FROM (
            SELECT site_id, trophic_group, AVG(biomass_kgha) AS biomass_kgha_tg
            FROM fb_se_trophic_groups
            GROUP BY site_id, trophic_group
            ORDER BY site_id
        ) AS tgs
        GROUP BY site_id
    ) AS site_tgs
    ON (site_sus.site_id = site_tgs.site_id)
) fb ON (site.id = fb.site_id)

LEFT JOIN (
    SELECT su_count.site_id, 
    sample_unit_count, 
    percent_avgs
    FROM (
        SELECT site_id, COUNT(*) AS sample_unit_count
        FROM (
            SELECT site_id
            FROM sample_event
            INNER JOIN transect_benthic ON (sample_event.id = transect_benthic.sample_event_id)
            INNER JOIN transectmethod_benthiclit t ON (transect_benthic.id = t.transect_id)
            GROUP BY sample_event.site_id, sample_event.management_id, sample_event.sample_date, number
        ) AS sc GROUP BY site_id
    ) AS su_count
    INNER JOIN (
        SELECT site_id, 
        json_agg(json_build_object(name, avg)) AS percent_avgs 
        FROM (
            SELECT site_id, name, 
            ROUND(AVG(cat_percent), 3) as avg
            FROM (
                WITH cps AS (
                    SELECT 
                    sample_event.site_id,
                    sample_event.management_id,
                    sample_event.sample_date,
                    transect_benthic.number,
                    c.id AS cat_id, 
                    c.name, 
                    SUM(o.length) AS category_length
                    FROM obs_benthiclit o
                    INNER JOIN (
                        WITH RECURSIVE tree(child, root) AS (
                            SELECT c.id, c.id
                            FROM benthic_attribute c
                            LEFT JOIN benthic_attribute p ON (c.parent_id = p.id)
                            WHERE p.id IS NULL
                            UNION
                            SELECT id, root
                            FROM tree
                            INNER JOIN benthic_attribute ON (tree.child = benthic_attribute.parent_id)
                        )
                        SELECT * FROM tree
                    ) category ON (o.attribute_id = category.child)
                    INNER JOIN benthic_attribute c ON (category.root = c.id)
                    INNER JOIN transectmethod_benthiclit t ON (o.benthiclit_id = t.transectmethod_ptr_id)
                    INNER JOIN transect_benthic ON (t.transect_id = transect_benthic.id)
                    INNER JOIN sample_event ON (transect_benthic.sample_event_id = sample_event.id)
                    -- field definition of sample event
                    GROUP BY sample_event.site_id, sample_event.management_id, sample_event.sample_date, 
                    transect_benthic.number, c.id
                )
                SELECT cps.site_id, cps.management_id, cps.sample_date, cps.number, cps.name,
                cps.category_length / cat_totals.su_length AS cat_percent
                FROM cps
                INNER JOIN (
                    SELECT site_id, management_id, sample_date, number, SUM(category_length) AS su_length
                    FROM cps
                    GROUP BY site_id, management_id, sample_date, number
                ) cat_totals ON (cps.site_id = cat_totals.site_id AND 
                                cps.management_id = cat_totals.management_id AND 
                                cps.sample_date = cat_totals.sample_date AND 
                                cps.number = cat_totals.number)
            ) AS cat_percents
            GROUP BY site_id, name
        ) AS site_percents
        GROUP BY site_id
    ) AS site_percents ON (su_count.site_id = site_percents.site_id)
) bl ON (site.id = bl.site_id)

LEFT JOIN (
    SELECT su_count.site_id, 
    sample_unit_count, 
    percent_avgs
    FROM (
        SELECT site_id, COUNT(*) AS sample_unit_count
        FROM (
            SELECT site_id
            FROM sample_event
            INNER JOIN transect_benthic ON (sample_event.id = transect_benthic.sample_event_id)
            INNER JOIN transectmethod_benthicpit t ON (transect_benthic.id = t.transect_id)
            GROUP BY sample_event.site_id, sample_event.management_id, sample_event.sample_date, number
        ) AS sc GROUP BY site_id
    ) AS su_count
    INNER JOIN (
        SELECT site_id, 
        json_agg(json_build_object(name, avg)) AS percent_avgs 
        FROM (
            SELECT site_id, name, 
            ROUND(AVG(cat_percent), 3) as avg
            FROM (
                WITH cps AS (
                    SELECT 
                    sample_event.site_id,
                    sample_event.management_id,
                    sample_event.sample_date,
                    transect_benthic.number,
                    t.interval_size,
                    c.id AS cat_id, 
                    c.name, 
                    SUM(t.interval_size) AS category_length
                    FROM obs_benthicpit o
                    INNER JOIN (
                        WITH RECURSIVE tree(child, root) AS (
                            SELECT c.id, c.id
                            FROM benthic_attribute c
                            LEFT JOIN benthic_attribute p ON (c.parent_id = p.id)
                            WHERE p.id IS NULL
                            UNION
                            SELECT id, root
                            FROM tree
                            INNER JOIN benthic_attribute ON (tree.child = benthic_attribute.parent_id)
                        )
                        SELECT * FROM tree
                    ) category ON (o.attribute_id = category.child)
                    INNER JOIN benthic_attribute c ON (category.root = c.id)
                    INNER JOIN transectmethod_benthicpit t ON (o.benthicpit_id = t.transectmethod_ptr_id)
                    INNER JOIN transect_benthic ON (t.transect_id = transect_benthic.id)
                    INNER JOIN sample_event ON (transect_benthic.sample_event_id = sample_event.id)
                    -- field definition of sample event
                    GROUP BY sample_event.site_id, sample_event.management_id, sample_event.sample_date, 
                    transect_benthic.number, t.interval_size, c.id
                )
                SELECT cps.site_id, cps.management_id, cps.sample_date, cps.number, cps.name,
                cps.category_length / cat_totals.su_length AS cat_percent
                FROM cps
                INNER JOIN (
                    SELECT site_id, management_id, sample_date, number, SUM(category_length) AS su_length
                    FROM cps
                    GROUP BY site_id, management_id, sample_date, number
                ) cat_totals ON (cps.site_id = cat_totals.site_id AND 
                                cps.management_id = cat_totals.management_id AND 
                                cps.sample_date = cat_totals.sample_date AND 
                                cps.number = cat_totals.number)
            ) AS cat_percents
            GROUP BY site_id, name
        ) AS site_percents
        GROUP BY site_id
    ) AS site_percents ON (su_count.site_id = site_percents.site_id)
) bp ON (site.id = bp.site_id)

LEFT JOIN (
    SELECT site_id, 
    COUNT(se.*) as sample_unit_count, 
    ROUND(AVG(se.score_avg), 1) AS score_avg
    FROM (SELECT 
        sample_event.site_id,
        sample_event.management_id,
        sample_event.sample_date,
        transect_benthic.number,
        AVG(s.val) AS score_avg
        FROM obs_habitatcomplexity o
        INNER JOIN api_habitatcomplexityscore s ON (o.score_id = s.id)
        INNER JOIN transectmethod_habitatcomplexity t ON (o.habitatcomplexity_id = t.transectmethod_ptr_id)
        INNER JOIN transect_benthic ON (t.transect_id = transect_benthic.id)
        INNER JOIN sample_event ON transect_benthic.sample_event_id = sample_event.id
        GROUP BY sample_event.site_id, sample_event.management_id, sample_event.sample_date, transect_benthic.number
    ) se
    GROUP BY se.site_id
) hc ON (site.id = hc.site_id)

LEFT JOIN (
    SELECT site_id, 
    COUNT(se.*) as sample_unit_count, 
    ROUND(AVG(se.count_total), 1) AS avg_count_total,
    ROUND(AVG(se.count_genera), 1) AS avg_count_genera,
    ROUND(AVG(se.percent_normal), 1) AS avg_percent_normal,
    ROUND(AVG(se.percent_pale), 1) AS avg_percent_pale,
    ROUND(AVG(se.percent_bleached), 1) AS avg_percent_bleached
    FROM (SELECT
        sample_event.site_id,
        sample_event.management_id,
        sample_event.sample_date,
        SUM(count_normal + count_pale + count_20 + count_50 + count_80 + count_100 + count_dead) AS count_total,
        COUNT(DISTINCT attribute_id) AS count_genera,
        ROUND((100 * SUM(count_normal) / CASE WHEN SUM(count_normal + count_pale + count_20 + count_50 + count_80 + 
        count_100 + count_dead) = 0 THEN 1 ELSE SUM(count_normal + count_pale + count_20 + count_50 + count_80 + 
        count_100 + count_dead) END), 1) AS percent_normal,
        ROUND((100 * SUM(count_pale) / CASE WHEN SUM(count_normal + count_pale + count_20 + count_50 + count_80 + 
        count_100 + count_dead) = 0 THEN 1 ELSE SUM(count_normal + count_pale + count_20 + count_50 + count_80 + 
        count_100 + count_dead) END), 1) AS percent_pale,
        ROUND((100 * SUM(count_20 + count_50 + count_80 + count_100 + count_dead) / CASE WHEN SUM(count_normal + 
        count_pale + count_20 + count_50 + count_80 + count_100 + count_dead) = 0 THEN 1 ELSE SUM(count_normal + 
        count_pale + count_20 + count_50 + count_80 + count_100 + count_dead) END), 1) AS percent_bleached
        FROM obs_colonies_bleached o
        INNER JOIN transectmethod_bleaching_quadrat_collection t ON (o.bleachingquadratcollection_id = 
        t.transectmethod_ptr_id)
        INNER JOIN quadrat_collection ON (t.quadrat_id = quadrat_collection.id)
        INNER JOIN sample_event ON (quadrat_collection.sample_event_id = sample_event.id)
        -- field definition of sample event
        GROUP BY sample_event.site_id, sample_event.management_id, sample_event.sample_date
    ) se
    GROUP BY se.site_id
) qccb ON (site.id = qccb.site_id)

LEFT JOIN (
    SELECT site_id, 
    COUNT(se.*) as sample_unit_count,
    ROUND(AVG(avg_percent_hard), 1) AS avg_percent_hard,
    ROUND(AVG(avg_percent_soft), 1) AS avg_percent_soft,
    ROUND(AVG(avg_percent_algae), 1) AS avg_percent_algae,
    ROUND(AVG(quadrat_count), 1) AS avg_quadrat_count
    FROM (SELECT
        sample_event.site_id,
        sample_event.management_id,
        sample_event.sample_date,
        ROUND(AVG(percent_hard), 1) AS avg_percent_hard, 
        ROUND(AVG(percent_soft), 1) AS avg_percent_soft, 
        ROUND(AVG(percent_algae), 1) AS avg_percent_algae,
        COUNT(*) AS quadrat_count
        FROM obs_quadrat_benthic_percent o
        INNER JOIN transectmethod_bleaching_quadrat_collection t ON (o.bleachingquadratcollection_id = 
        t.transectmethod_ptr_id)
        INNER JOIN quadrat_collection ON (t.quadrat_id = quadrat_collection.id)
        INNER JOIN sample_event ON (quadrat_collection.sample_event_id = sample_event.id)
        -- field definition of sample event
        GROUP BY sample_event.site_id, sample_event.management_id, sample_event.sample_date
    ) se
    GROUP BY se.site_id
) qcbp ON(site.id = qcbp.site_id);

CREATE UNIQUE INDEX ON vw_summary_site (site_id);
    """

    name_family = models.CharField(max_length=100)
    name_genus = models.CharField(max_length=100)
    name = models.CharField(max_length=100)
    biomass_constant_a = models.DecimalField(
        max_digits=7, decimal_places=6, null=True, blank=True
    )
    biomass_constant_b = models.DecimalField(
        max_digits=7, decimal_places=6, null=True, blank=True
    )
    biomass_constant_c = models.DecimalField(
        max_digits=7, decimal_places=6, default=1, null=True, blank=True
    )
    trophic_group = models.CharField(max_length=100, blank=True)
    trophic_level = models.DecimalField(
        max_digits=3, decimal_places=2, null=True, blank=True
    )
    functional_group = models.CharField(max_length=100, blank=True)
    vulnerability = models.DecimalField(
        max_digits=4, decimal_places=2, null=True, blank=True
    )

    class Meta:
        db_table = "vw_fish_attributes"
        managed = False


class SampleEventViewModel(models.Model):
    sql = """
CREATE OR REPLACE VIEW public.vw_sample_events
 AS
 SELECT project.id AS project_id,
    project.name AS project_name,
    project.status AS project_status,
    project.notes AS project_notes,
    'https://datamermaid.org/contact-project/?project_id='::text || COALESCE(project.id::text, ''::text) AS 
    contact_link,
    tags.tags,
    se.site_id,
    site.name AS site_name,
    site.location,
    site.notes AS site_notes,
    country.id AS country_id,
    country.name AS country_name,
    rt.name AS reef_type,
    rz.name AS reef_zone,
    re.name AS reef_exposure,
    m.id AS management_id,
    m.name AS management_name,
    m.name_secondary AS management_name_secondary,
    m.est_year AS management_est_year,
    m.size AS management_size,
    parties.parties AS management_parties,
    mc.name AS management_compliance,
    array_to_json(array_remove(ARRAY[
        CASE
            WHEN m.no_take THEN 'no take'::text
            ELSE NULL::text
        END,
        CASE
            WHEN m.open_access THEN 'open access'::text
            ELSE NULL::text
        END,
        CASE
            WHEN m.gear_restriction THEN 'gear restriction'::text
            ELSE NULL::text
        END,
        CASE
            WHEN m.periodic_closure THEN 'periodic closure'::text
            ELSE NULL::text
        END,
        CASE
            WHEN m.size_limits THEN 'size limits'::text
            ELSE NULL::text
        END,
        CASE
            WHEN m.species_restriction THEN 'species restriction'::text
            ELSE NULL::text
        END,
        CASE
            WHEN m.access_restriction THEN 'access restriction'::text
            ELSE NULL::text
        END
        ], NULL::text))::jsonb AS management_rules,
    m.notes AS management_notes,
    se.id AS sample_event_id,
    se.sample_date,
    se.sample_time,
    c.name AS current_name,
    t.name AS tide_name,
    v.name AS visibility_name,
    se.depth,
    se.notes AS sample_event_notes,
    CASE
        WHEN project.data_policy_beltfish = 10 THEN 'private'::text
        WHEN project.data_policy_beltfish = 50 THEN 'public summary'::text
        WHEN project.data_policy_beltfish = 100 THEN 'public'::text
        ELSE ''::text
    END AS data_policy_beltfish,
    CASE
        WHEN project.data_policy_benthiclit = 10 THEN 'private'::text
        WHEN project.data_policy_benthiclit = 50 THEN 'public summary'::text
        WHEN project.data_policy_benthiclit = 100 THEN 'public'::text
        ELSE ''::text
    END AS data_policy_benthiclit,
    CASE
        WHEN project.data_policy_benthicpit = 10 THEN 'private'::text
        WHEN project.data_policy_benthicpit = 50 THEN 'public summary'::text
        WHEN project.data_policy_benthicpit = 100 THEN 'public'::text
        ELSE ''::text
    END AS data_policy_benthicpit,
    CASE
        WHEN project.data_policy_habitatcomplexity = 10 THEN 'private'::text
        WHEN project.data_policy_habitatcomplexity = 50 THEN 'public summary'::text
        WHEN project.data_policy_habitatcomplexity = 100 THEN 'public'::text
        ELSE ''::text
    END AS data_policy_habitatcomplexity,
    CASE
        WHEN project.data_policy_bleachingqc = 10 THEN 'private'::text
        WHEN project.data_policy_bleachingqc = 50 THEN 'public summary'::text
        WHEN project.data_policy_bleachingqc = 100 THEN 'public'::text
        ELSE ''::text
    END AS data_policy_bleachingqc

    FROM sample_event se
     LEFT JOIN api_current c ON se.current_id = c.id
     LEFT JOIN api_tide t ON se.tide_id = t.id
     LEFT JOIN api_visibility v ON se.visibility_id = v.id
     JOIN site ON se.site_id = site.id
     JOIN project ON site.project_id = project.id
     LEFT JOIN ( SELECT project_1.id,
            jsonb_agg(jsonb_build_object('id', t_1.id, 'name', t_1.name)) AS tags
           FROM api_uuidtaggeditem ti
             JOIN django_content_type ct ON ti.content_type_id = ct.id
             JOIN project project_1 ON ti.object_id = project_1.id
             JOIN api_tag t_1 ON ti.tag_id = t_1.id
          WHERE ct.app_label::text = 'api'::text AND ct.model::text = 'project'::text
          GROUP BY project_1.id) tags ON project.id = tags.id
     JOIN country ON site.country_id = country.id
     LEFT JOIN api_reeftype rt ON site.reef_type_id = rt.id
     LEFT JOIN api_reefzone rz ON site.reef_zone_id = rz.id
     LEFT JOIN api_reefexposure re ON site.exposure_id = re.id
     JOIN management m ON se.management_id = m.id
     LEFT JOIN management_compliance mc ON m.compliance_id = mc.id
     LEFT JOIN ( SELECT mps.management_id,
            jsonb_agg(mp.name ORDER BY mp.name) AS parties
           FROM management_parties mps
             JOIN management_party mp ON mps.managementparty_id = mp.id
          GROUP BY mps.management_id) parties ON m.id = parties.management_id;
    """

    class Meta:
        db_table = "vw_sample_events"
        managed = False


class BaseViewModel(models.Model):
    project_lookup = "project_id"
    se_fields = [
        "project_id",
        "project_name",
        "project_status",
        "project_notes",
        "contact_link",
        "tags",
        "site_id",
        "site_name",
        "location",
        "site_notes",
        "country_id",
        "country_name",
        "reef_type",
        "reef_zone",
        "reef_exposure",
        "management_id",
        "management_name",
        "management_name_secondary",
        "management_est_year",
        "management_size",
        "management_parties",
        "management_compliance",
        "management_rules",
        "management_notes",
        "sample_date",
        "depth",
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project_id = models.UUIDField()
    project_name = models.CharField(max_length=255)
    project_status = models.PositiveSmallIntegerField(
        choices=Project.STATUSES, default=Project.OPEN
    )
    project_notes = models.TextField(blank=True)
    contact_link = models.CharField(max_length=255)
    tags = JSONField(null=True, blank=True)
    site_id = models.UUIDField()
    site_name = models.CharField(max_length=255)
    location = models.PointField(srid=4326)
    site_notes = models.TextField(blank=True)
    country_id = models.UUIDField()
    country_name = models.CharField(max_length=50)
    reef_type = models.CharField(max_length=50)
    reef_zone = models.CharField(max_length=50)
    reef_exposure = models.CharField(max_length=50)
    management_id = models.UUIDField()
    management_name = models.CharField(max_length=255)
    management_name_secondary = models.CharField(max_length=255)
    management_est_year = models.PositiveSmallIntegerField()
    management_size = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        verbose_name=_(u"Size (ha)"),
        null=True,
        blank=True,
    )
    management_parties = JSONField(null=True, blank=True)
    management_compliance = models.CharField(max_length=100)
    management_rules = JSONField(null=True, blank=True)
    management_notes = models.TextField(blank=True)
    sample_date = models.DateField()
    current_name = models.CharField(max_length=50)
    tide_name = models.CharField(max_length=50)
    visibility_name = models.CharField(max_length=50)

    class Meta:
        abstract = True
