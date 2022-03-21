import uuid

from django.contrib.gis.db import models
from django.contrib.postgres.fields import JSONField
from django.utils.translation import ugettext_lazy as _

from api.models import Project


project_where = """    WHERE\n        project.id = '%(project_id)s' :: uuid\n"""

sample_event_sql_template = f"""
    WITH tags AS (
        SELECT
            project_1.id,
            jsonb_agg(
                jsonb_build_object('id', t_1.id, 'name', t_1.name)
            ) AS tags
        FROM
            api_uuidtaggeditem ti
            JOIN django_content_type ct ON ti.content_type_id = ct.id
            JOIN project project_1 ON ti.object_id = project_1.id
            JOIN api_tag t_1 ON ti.tag_id = t_1.id
        WHERE
            ct.app_label :: text = 'api' :: text
            AND ct.model :: text = 'project' :: text
        GROUP BY
            project_1.id
    ),
    parties AS (
        SELECT
            mps.management_id,
            jsonb_agg(
                mp.name
                ORDER BY
                    mp.name
            ) AS parties
        FROM
            management_parties mps
        INNER JOIN management_party mp ON mps.managementparty_id = mp.id
        INNER JOIN
            management
        ON (management.id = mps.management_id)
        WHERE
            management.project_id = '%(project_id)s' :: uuid
        GROUP BY
            mps.management_id
    ),
    site_covariates AS (
        SELECT
            cov.site_id,
            jsonb_agg(
                jsonb_build_object(
                    'id',
                    cov.id,
                    'name',
                    cov.name,
                    'value',
                    cov.value,
                    'datestamp',
                    cov.datestamp,
                    'requested_datestamp',
                    cov.requested_datestamp
                )
            ) AS covariates
        FROM
            api_covariate as cov
        INNER JOIN
            site
        ON (site.id = cov.site_id)
        WHERE
            site.project_id = '%(project_id)s' :: uuid
        GROUP BY
            cov.site_id
    )
    SELECT
        project.id AS project_id,
        project.name AS project_name,
        project.status AS project_status,
        project.notes AS project_notes,
        'https://datamermaid.org/contact-project?project_id=' :: text ||
            COALESCE(project.id :: text, '' :: text) AS contact_link,
        tags.tags,
        se.site_id,
        site.name AS site_name,
        site.location,
        ST_X(site.location) AS longitude,
        ST_Y(site.location) AS latitude,
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
        array_to_json(
            array_remove(
                ARRAY [
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
            END],
                NULL :: text
            )
        ) :: jsonb AS management_rules,
        m.notes AS management_notes,
        se.id AS sample_event_id,
        se.sample_date,
        se.notes AS sample_event_notes,
        CASE
            WHEN project.data_policy_beltfish = 10 THEN 'private' :: text
            WHEN project.data_policy_beltfish = 50 THEN 'public summary' :: text
            WHEN project.data_policy_beltfish = 100 THEN 'public' :: text
            ELSE '' :: text
        END AS data_policy_beltfish,
        CASE
            WHEN project.data_policy_benthiclit = 10 THEN 'private' :: text
            WHEN project.data_policy_benthiclit = 50 THEN 'public summary' :: text
            WHEN project.data_policy_benthiclit = 100 THEN 'public' :: text
            ELSE '' :: text
        END AS data_policy_benthiclit,
        CASE
            WHEN project.data_policy_benthicpit = 10 THEN 'private' :: text
            WHEN project.data_policy_benthicpit = 50 THEN 'public summary' :: text
            WHEN project.data_policy_benthicpit = 100 THEN 'public' :: text
            ELSE '' :: text
        END AS data_policy_benthicpit,
        CASE
            WHEN project.data_policy_habitatcomplexity = 10 THEN 'private' :: text
            WHEN project.data_policy_habitatcomplexity = 50 THEN 'public summary' :: text
            WHEN project.data_policy_habitatcomplexity = 100 THEN 'public' :: text
            ELSE '' :: text
        END AS data_policy_habitatcomplexity,
        CASE
            WHEN project.data_policy_bleachingqc = 10 THEN 'private' :: text
            WHEN project.data_policy_bleachingqc = 50 THEN 'public summary' :: text
            WHEN project.data_policy_bleachingqc = 100 THEN 'public' :: text
            ELSE '' :: text
        END AS data_policy_bleachingqc,
        site_covariates.covariates
    FROM
        sample_event se
        JOIN site ON se.site_id = site.id
        JOIN project ON site.project_id = project.id
        LEFT JOIN tags ON project.id = tags.id
        JOIN country ON site.country_id = country.id
        LEFT JOIN api_reeftype rt ON site.reef_type_id = rt.id
        LEFT JOIN api_reefzone rz ON site.reef_zone_id = rz.id
        LEFT JOIN api_reefexposure re ON site.exposure_id = re.id
        JOIN management m ON se.management_id = m.id
        LEFT JOIN management_compliance mc ON m.compliance_id = mc.id
        LEFT JOIN parties ON m.id = parties.management_id
        LEFT JOIN site_covariates ON site.id = site_covariates.site_id
    {project_where}
"""


class BaseSQLModel(models.Model):
    se_fields = [
        "project_id",
        "project_name",
        "project_status",
        "project_notes",
        "contact_link",
        "tags",
        "site_id",
        "site_name",
        "covariates",
        "location",
        "longitude",
        "latitude",
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
        "sample_event_id",
        "sample_date",
        "sample_event_notes",
    ]

    # SU aggregation SQL common to all SEs
    su_aggfields_sql = """
        ROUND(AVG("depth"), 2) as depth_avg,
        string_agg(DISTINCT current_name, ', ' ORDER BY current_name) AS current_name,
        string_agg(DISTINCT tide_name, ', ' ORDER BY tide_name) AS tide_name,
        string_agg(DISTINCT visibility_name, ', ' ORDER BY visibility_name) AS visibility_name
    """

    # model fields to be inherited by every obs/su/se view
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
    longitude = models.FloatField()
    latitude = models.FloatField()
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
        verbose_name=_("Size (ha)"),
        null=True,
        blank=True,
    )
    management_parties = JSONField(null=True, blank=True)
    management_compliance = models.CharField(max_length=100)
    management_rules = JSONField(null=True, blank=True)
    management_notes = models.TextField(blank=True)
    sample_date = models.DateField()
    sample_event_id = models.UUIDField()
    sample_event_notes = models.TextField(blank=True)
    covariates = JSONField(null=True, blank=True)

    class Meta:
        abstract = True


class BaseSUSQLModel(BaseSQLModel):
    # Unique combination of these fields defines a single (pseudo) sample unit.
    # Corresponds to *SUSQLModel.su_fields
    transect_su_fields = [
        "su.sample_event_id",
        "su.depth",
        "su.number",
        "su.len_surveyed",
    ]
    qc_su_fields = [
        "sample_event_id",
        "depth",
        "quadrat_size",
    ]

    # SU sql common to all obs-level views
    su_fields_sql = """
        su.id AS sample_unit_id,
        su.depth,
        su.label,
        r.name AS relative_depth,
        su.sample_time,
        observers.observers,
        c.name AS current_name,
        t.name AS tide_name,
        v.name AS visibility_name
    """

    # SU aggregation SQL common to all SU-level views
    su_aggfields_sql = """
        string_agg(DISTINCT label::text, ', '::text ORDER BY (label::text)) AS label,
        string_agg(DISTINCT relative_depth::text, ', '::text ORDER BY (relative_depth::text)) AS relative_depth,
        string_agg(DISTINCT sample_time::text, ', '::text ORDER BY (sample_time::text)) AS sample_time,
        string_agg(DISTINCT current_name::text, ', '::text ORDER BY (current_name::text)) AS current_name,
        string_agg(DISTINCT tide_name::text, ', '::text ORDER BY (tide_name::text)) AS tide_name,
        string_agg(DISTINCT visibility_name::text, ', '::text ORDER BY (visibility_name::text)) AS visibility_name
    """

    # Fields common to all SUs that are actually SU properties (that make SUs distinct)
    depth = models.DecimalField(
        max_digits=3, decimal_places=1, verbose_name=_("depth (m)")
    )
    # Fields common to all SUs that are aggregated from actual SUs into pseudo-SUs
    agg_su_fields = [
        "sample_unit_ids",
        "label",
        "relative_depth",
        "sample_time",
        "observers",
        "current_name",
        "tide_name",
        "visibility_name",
    ]
    # SU-level BaseSUSQLModel inheritors should instantiate sample_unit_ids; obs-level inheritors shouldn't
    label = models.CharField(max_length=50, blank=True)
    relative_depth = models.CharField(max_length=50)
    sample_time = models.TimeField()
    observers = JSONField(null=True, blank=True)
    current_name = models.CharField(max_length=50)
    tide_name = models.CharField(max_length=50)
    visibility_name = models.CharField(max_length=50)

    class Meta:
        abstract = True
