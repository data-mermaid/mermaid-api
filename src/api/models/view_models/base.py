import uuid
from django.contrib.gis.db import models
from django.contrib.postgres.fields import JSONField
from django.utils.translation import ugettext_lazy as _
from ..mermaid import Project, FishAttribute


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
    WHEN fish_grouping IS NOT NULL THEN fish_grouping.name::text
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
    WHEN fish_grouping.name IS NOT NULL THEN ROUND((
        SELECT
        AVG(biomass_constant_a) AS biomass_constant_a
        FROM (
            SELECT DISTINCT fish_species.fishattribute_ptr_id, biomass_constant_a
            FROM fish_species
            INNER JOIN fish_genus ON (fish_species.genus_id = fish_genus.fishattribute_ptr_id) 
            INNER JOIN api_fishgroupingrelationship r ON (
                fish_species.fishattribute_ptr_id = r.attribute_id
                OR fish_species.genus_id = r.attribute_id
                OR fish_genus.family_id = r.attribute_id
            )
            WHERE r.grouping_id = fish_grouping.fishattribute_ptr_id
        ) AS species_constant_as
    ), 6)
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
    WHEN fish_grouping.name IS NOT NULL THEN ROUND((
        SELECT
        AVG(biomass_constant_b) AS biomass_constant_b
        FROM (
            SELECT DISTINCT fish_species.fishattribute_ptr_id, biomass_constant_b
            FROM fish_species
            INNER JOIN fish_genus ON (fish_species.genus_id = fish_genus.fishattribute_ptr_id) 
            INNER JOIN api_fishgroupingrelationship r ON (
                fish_species.fishattribute_ptr_id = r.attribute_id
                OR fish_species.genus_id = r.attribute_id
                OR fish_genus.family_id = r.attribute_id
            )
            WHERE r.grouping_id = fish_grouping.fishattribute_ptr_id
        ) AS species_constant_bs
    ), 6)
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
    WHEN fish_grouping.name IS NOT NULL THEN ROUND((
        SELECT
        AVG(biomass_constant_c) AS biomass_constant_c
        FROM (
            SELECT DISTINCT fish_species.fishattribute_ptr_id, biomass_constant_c
            FROM fish_species
            INNER JOIN fish_genus ON (fish_species.genus_id = fish_genus.fishattribute_ptr_id) 
            INNER JOIN api_fishgroupingrelationship r ON (
                fish_species.fishattribute_ptr_id = r.attribute_id
                OR fish_species.genus_id = r.attribute_id
                OR fish_genus.family_id = r.attribute_id
            )
            WHERE r.grouping_id = fish_grouping.fishattribute_ptr_id
        ) AS species_constant_cs
    ), 6)
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
    WHEN fish_grouping.name IS NOT NULL THEN (
        SELECT "name"
        FROM (
            SELECT fish_group_trophic.name, COUNT(*) AS freq
            FROM fish_species
            INNER JOIN fish_group_trophic ON (fish_species.trophic_group_id = fish_group_trophic.id)
            INNER JOIN fish_genus ON (fish_species.genus_id = fish_genus.fishattribute_ptr_id) 
            INNER JOIN api_fishgroupingrelationship r ON (
                fish_species.fishattribute_ptr_id = r.attribute_id
                OR fish_species.genus_id = r.attribute_id
                OR fish_genus.family_id = r.attribute_id
            )
            WHERE r.grouping_id = fish_grouping.fishattribute_ptr_id
            GROUP BY fish_group_trophic.name
            ORDER BY (COUNT(*)) DESC, fish_group_trophic.name
            LIMIT 1
        ) AS species_trophic_groups
    )
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
    WHEN fish_grouping.name IS NOT NULL THEN (
        SELECT "name"
        FROM (
            SELECT fish_group_function.name, COUNT(*) AS freq
            FROM fish_species
            INNER JOIN fish_group_function ON (fish_species.functional_group_id = fish_group_function.id)
            INNER JOIN fish_genus ON (fish_species.genus_id = fish_genus.fishattribute_ptr_id) 
            INNER JOIN api_fishgroupingrelationship r ON (
                fish_species.fishattribute_ptr_id = r.attribute_id
                OR fish_species.genus_id = r.attribute_id
                OR fish_genus.family_id = r.attribute_id
            )
            WHERE r.grouping_id = fish_grouping.fishattribute_ptr_id
            GROUP BY fish_group_function.name
            ORDER BY (COUNT(*)) DESC, fish_group_function.name
            LIMIT 1
        ) AS species_functional_groups
    )
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
    WHEN fish_grouping.name IS NOT NULL THEN ROUND((
        SELECT
        AVG(trophic_level) AS trophic_level
        FROM (
            SELECT DISTINCT fish_species.fishattribute_ptr_id, trophic_level
            FROM fish_species
            INNER JOIN fish_genus ON (fish_species.genus_id = fish_genus.fishattribute_ptr_id) 
            INNER JOIN api_fishgroupingrelationship r ON (
                fish_species.fishattribute_ptr_id = r.attribute_id
                OR fish_species.genus_id = r.attribute_id
                OR fish_genus.family_id = r.attribute_id
            )
            WHERE r.grouping_id = fish_grouping.fishattribute_ptr_id
        ) AS species_trophic_levels
    ), 2)
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
    WHEN fish_grouping.name IS NOT NULL THEN ROUND((
        SELECT
        AVG(vulnerability) AS vulnerability
        FROM (
            SELECT DISTINCT fish_species.fishattribute_ptr_id, vulnerability
            FROM fish_species
            INNER JOIN fish_genus ON (fish_species.genus_id = fish_genus.fishattribute_ptr_id) 
            INNER JOIN api_fishgroupingrelationship r ON (
                fish_species.fishattribute_ptr_id = r.attribute_id
                OR fish_species.genus_id = r.attribute_id
                OR fish_genus.family_id = r.attribute_id
            )
            WHERE r.grouping_id = fish_grouping.fishattribute_ptr_id
        ) AS species_vulnerabilities
    ), 2)
    ELSE NULL::numeric
END AS vulnerability

FROM fish_attribute
LEFT JOIN fish_species ON fish_attribute.id = fish_species.fishattribute_ptr_id
LEFT JOIN fish_genus species_genus ON fish_species.genus_id = species_genus.fishattribute_ptr_id
LEFT JOIN fish_family species_genus_family ON species_genus.family_id = species_genus_family.fishattribute_ptr_id
LEFT JOIN fish_genus ON fish_attribute.id = fish_genus.fishattribute_ptr_id
LEFT JOIN fish_family genus_family ON fish_genus.family_id = genus_family.fishattribute_ptr_id
LEFT JOIN fish_family ON fish_attribute.id = fish_family.fishattribute_ptr_id
LEFT JOIN fish_grouping ON (fish_attribute.id = fish_grouping.fishattribute_ptr_id)
LEFT JOIN fish_group_trophic ON fish_species.trophic_group_id = fish_group_trophic.id
LEFT JOIN fish_group_function ON fish_species.functional_group_id = fish_group_function.id

ORDER BY (
    CASE
        WHEN fish_species.name IS NOT NULL THEN concat(species_genus.name, ' ', fish_species.name)
        WHEN fish_genus.name IS NOT NULL THEN fish_genus.name::text
        WHEN fish_family.name IS NOT NULL THEN fish_family.name::text
        ELSE NULL::text
    END);
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
