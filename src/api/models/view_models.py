import uuid
from django.contrib.gis.db import models
from django.contrib.postgres.fields import JSONField
from django.utils.translation import ugettext_lazy as _

from . import FishAttribute
from .base import ExtendedManager
from .mermaid import Project


class FishAttributeView(FishAttribute):
    sql = """
DROP VIEW IF EXISTS public.vw_fish_attributes;
CREATE OR REPLACE VIEW public.vw_fish_attributes
 AS
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
        ELSE NULL::numeric
    END AS vulnerability
FROM fish_attribute
LEFT JOIN fish_species ON fish_attribute.id = fish_species.fishattribute_ptr_id
LEFT JOIN fish_genus species_genus ON fish_species.genus_id = species_genus.fishattribute_ptr_id
LEFT JOIN fish_family species_genus_family ON species_genus.family_id = species_genus_family.fishattribute_ptr_id
LEFT JOIN fish_genus ON fish_attribute.id = fish_genus.fishattribute_ptr_id
LEFT JOIN fish_family genus_family ON fish_genus.family_id = genus_family.fishattribute_ptr_id
LEFT JOIN fish_family ON fish_attribute.id = fish_family.fishattribute_ptr_id
LEFT JOIN fish_group_trophic ON fish_species.trophic_group_id = fish_group_trophic.id
LEFT JOIN fish_group_function ON fish_species.functional_group_id = fish_group_function.id
ORDER BY (
    CASE
        WHEN fish_species.name IS NOT NULL THEN concat(species_genus.name, ' ', fish_species.name)
        WHEN fish_genus.name IS NOT NULL THEN fish_genus.name::text
        WHEN fish_family.name IS NOT NULL THEN fish_family.name::text
        ELSE NULL::text
    END);

ALTER TABLE public.vw_fish_attributes
    OWNER TO postgres;
    """

    name_family = models.CharField(max_length=100)
    name_genus = models.CharField(max_length=100)
    name = models.CharField(max_length=100)
    biomass_constant_a = models.DecimalField(max_digits=7, decimal_places=6,
                                             null=True, blank=True)
    biomass_constant_b = models.DecimalField(max_digits=7, decimal_places=6,
                                             null=True, blank=True)
    biomass_constant_c = models.DecimalField(max_digits=7, decimal_places=6, default=1,
                                             null=True, blank=True)
    trophic_group = models.CharField(max_length=100, blank=True)
    trophic_level = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    functional_group = models.CharField(max_length=100, blank=True)
    vulnerability = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = 'vw_fish_attributes'
        managed = False


class BaseViewModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True

    objects = ExtendedManager()


class BeltFishObsView(BaseViewModel):
    project_lookup = "project_id"

    sql = """
DROP VIEW IF EXISTS public.vw_beltfish_obs;
CREATE OR REPLACE VIEW public.vw_beltfish_obs
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
        END], NULL::text))::jsonb AS management_rules,
    m.notes AS management_notes,
    se.id AS sample_event_id,
    se.sample_date,
    se.sample_time,
    c.name AS current_name,
    t.name AS tide_name,
    v.name AS visibility_name,
    se.depth,
    se.notes AS sample_event_notes,
    tt.transectmethod_ptr_id AS sample_unit_id,
    tbf.number,
    tbf.label,
    tbf.len_surveyed AS transect_len_surveyed,
    rs.name AS reef_slope,
    w.val AS transect_width,
    observers.observers,
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
    o.id,
    o.size,
    o.count,
    ROUND(
        (10 * o.count)::numeric * f.biomass_constant_a * ((o.size * f.biomass_constant_c) ^ f.biomass_constant_b) / 
        (tbf.len_surveyed * w.val)::numeric, 
        2
    )::numeric(7,2) AS biomass_kgha,
    o.notes AS observation_notes,
        CASE
            WHEN project.data_policy_beltfish = 10 THEN 'private'::text
            WHEN project.data_policy_beltfish = 50 THEN 'public summary'::text
            WHEN project.data_policy_beltfish = 100 THEN 'public'::text
            ELSE ''::text
        END AS data_policy_beltfish
   FROM obs_transectbeltfish o
     JOIN vw_fish_attributes f ON o.fish_attribute_id = f.id
     JOIN transectmethod_transectbeltfish tt ON o.beltfish_id = tt.transectmethod_ptr_id
     JOIN transect_belt_fish tbf ON tt.transect_id = tbf.id
     LEFT JOIN api_fishsizebin sb ON tbf.size_bin_id = sb.id
     LEFT JOIN api_reefslope rs ON tbf.reef_slope_id = rs.id
     JOIN api_belttransectwidth w ON tbf.width_id = w.id
     JOIN sample_event se ON tbf.sample_event_id = se.id
     LEFT JOIN api_current c ON se.current_id = c.id
     LEFT JOIN api_tide t ON se.tide_id = t.id
     LEFT JOIN api_visibility v ON se.visibility_id = v.id
     JOIN site ON se.site_id = site.id
     JOIN project ON site.project_id = project.id
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
          GROUP BY mps.management_id) parties ON m.id = parties.management_id
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
          GROUP BY tt_1.transect_id) observers ON tbf.id = observers.transect_id;

ALTER TABLE public.vw_beltfish_obs
    OWNER TO postgres;
    """

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
    sample_event_id = models.UUIDField()
    sample_date = models.DateField()
    sample_time = models.TimeField()
    current_name = models.CharField(max_length=50)
    tide_name = models.CharField(max_length=50)
    visibility_name = models.CharField(max_length=50)
    depth = models.DecimalField(
        max_digits=3, decimal_places=1, verbose_name=_(u"depth (m)")
    )
    sample_event_notes = models.TextField(blank=True)
    sample_unit_id = models.UUIDField()
    number = models.PositiveSmallIntegerField()
    label = models.CharField(max_length=50, blank=True)
    transect_len_surveyed = models.PositiveSmallIntegerField(
        verbose_name=_(u"transect length surveyed (m)")
    )
    reef_slope = models.CharField(max_length=50)
    transect_width = models.PositiveSmallIntegerField(null=True, blank=True)
    observers = JSONField(null=True, blank=True)
    fish_family = models.CharField(max_length=100)
    fish_genus = models.CharField(max_length=100)
    fish_taxon = models.CharField(max_length=100)
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
    size_bin = models.PositiveSmallIntegerField()
    size = models.DecimalField(
        max_digits=5, decimal_places=1, verbose_name=_(u"size (cm)")
    )
    count = models.PositiveIntegerField(default=1)
    biomass_kgha = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        verbose_name=_(u"biomass (kg/ha)"),
        null=True,
        blank=True,
    )
    observation_notes = models.TextField(blank=True)
    data_policy_beltfish = models.CharField(max_length=50)

    objects = ExtendedManager()

    class Meta:
        db_table = "vw_beltfish_obs"
        managed = False


class BeltFishSUView(BaseViewModel):
    project_lookup = "project_id"

    # NOT grouping by sample_event_id, sample_time, depth, sample_unit_id, transect_width, observers
    sql = """
DROP VIEW IF EXISTS public.vw_beltfish_su;
CREATE OR REPLACE VIEW public.vw_beltfish_su
 AS
SELECT 
NULL AS id,
project_id, project_name, project_status, project_notes, contact_link, tags, site_id, site_name, location, 
site_notes, country_id, country_name, reef_type, reef_zone, reef_exposure, management_id, management_name, 
management_name_secondary, management_est_year, management_size, management_parties, management_compliance, 
management_rules, management_notes, sample_date,  
sample_event_notes, "number", transect_len_surveyed, 
reef_slope, size_bin, data_policy_beltfish, 

SUM(biomass_kgha) AS biomass_kgha,
jsonb_object_agg(
    (CASE WHEN trophic_group IS NULL THEN 'other' ELSE trophic_group END), 
    ROUND(biomass_kgha, 2)
) AS biomass_kgha_by_trophic_group
 
FROM (
    SELECT project_id, project_name, project_status, project_notes, contact_link, tags, site_id, site_name, location, 
    site_notes, country_id, country_name, reef_type, reef_zone, reef_exposure, management_id, management_name, 
    management_name_secondary, management_est_year, management_size, management_parties, management_compliance, 
    management_rules, management_notes, sample_date,  
    sample_event_notes, "number", transect_len_surveyed, reef_slope, 
    size_bin, data_policy_beltfish, 
    trophic_group, 

    SUM(biomass_kgha) AS biomass_kgha
    
    FROM vw_beltfish_obs
    GROUP BY project_id, project_name, project_status, project_notes, contact_link, tags, site_id, site_name, location, 
    site_notes, country_id, country_name, reef_type, reef_zone, reef_exposure, management_id, management_name, 
    management_name_secondary, management_est_year, management_size, management_parties, management_compliance, 
    management_rules, management_notes, sample_date,  
    sample_event_notes, "number", transect_len_surveyed, reef_slope, 
    size_bin, data_policy_beltfish, 
    trophic_group
) AS beltfish_obs_tg

GROUP BY project_id, project_name, project_status, project_notes, contact_link, tags, site_id, site_name, location, 
site_notes, country_id, country_name, reef_type, reef_zone, reef_exposure, management_id, management_name, 
management_name_secondary, management_est_year, management_size, management_parties, management_compliance, 
management_rules, management_notes, sample_date, 
sample_event_notes, "number", transect_len_surveyed, reef_slope, 
size_bin, data_policy_beltfish;
    
ALTER TABLE public.vw_beltfish_su
    OWNER TO postgres;
    """

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
    sample_event_notes = models.TextField(blank=True)
    number = models.PositiveSmallIntegerField()
    transect_len_surveyed = models.PositiveSmallIntegerField(
        verbose_name=_(u"transect length surveyed (m)")
    )
    reef_slope = models.CharField(max_length=50)
    size_bin = models.PositiveSmallIntegerField()
    biomass_kgha = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name=_(u"biomass (kg/ha)"),
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
DROP VIEW IF EXISTS public.vw_beltfish_se;
CREATE OR REPLACE VIEW public.vw_beltfish_se
 AS
-- For each SE, summarize biomass by 1) avg of transects and 2) avg of transects' trophic groups
SELECT 
NULL AS id,
vw_beltfish_su.project_id, project_name, project_status, project_notes, contact_link, tags, 
vw_beltfish_su.site_id, site_name, "location", site_notes, 
country_id, country_name, 
reef_type, reef_zone, reef_exposure, 
vw_beltfish_su.management_id, management_name, management_name_secondary, management_est_year, management_size, 
management_parties, management_compliance, management_rules, management_notes, 
vw_beltfish_su.sample_date, sample_event_notes, data_policy_beltfish,
biomass_kgha_avg,
biomass_kgha_by_trophic_group_avg

FROM public.vw_beltfish_su

INNER JOIN (
    SELECT project_id, site_id, management_id, sample_date, ROUND(AVG(biomass_kgha), 2) AS biomass_kgha_avg
    FROM public.vw_beltfish_su
    GROUP BY project_id, site_id, management_id, sample_date
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
        SELECT project_id, site_id, management_id, sample_date, 
        tgdata.key AS tg, AVG(tgdata.value::float) AS biomass_kgha
        FROM public.vw_beltfish_su,
        jsonb_each_text(biomass_kgha_by_trophic_group) AS tgdata
        GROUP BY 
        project_id, site_id, management_id, sample_date, tgdata.key
    ) AS beltfish_su_tg
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
vw_beltfish_su.sample_date, sample_event_notes, data_policy_beltfish,
biomass_kgha_avg,
biomass_kgha_by_trophic_group_avg;

ALTER TABLE public.vw_beltfish_se
    OWNER TO postgres;
    """

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
    sample_event_notes = models.TextField(blank=True)
    biomass_kgha_avg = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name=_(u"biomass (kg/ha)"),
        null=True,
        blank=True,
    )
    biomass_kgha_by_trophic_group_avg = JSONField(null=True, blank=True)
    data_policy_beltfish = models.CharField(max_length=50)

    objects = ExtendedManager()

    class Meta:
        db_table = "vw_beltfish_se"
        managed = False
