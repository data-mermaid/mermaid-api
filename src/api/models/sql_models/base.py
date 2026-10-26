import uuid

from django.contrib.gis.db import models
from django.utils.translation import gettext_lazy as _

from api.models import (
    BLEACHING_CATEGORIES,
    BLEACHING_CATEGORY_HARD_CORAL,
    BLEACHING_CATEGORY_SOFT_CORAL,
    BLEACHING_STATUS_CHOICES,
    Project,
)

project_where = """project.id = '%(project_id)s'::uuid"""

# Inline bleaching status lookup with (val, name) columns, built from BLEACHING_STATUS_CHOICES
bleaching_status_sql = "(VALUES {}) AS bs(val, name)".format(
    ", ".join(f"({val}, '{name}')" for val, name in BLEACHING_STATUS_CHOICES)
)
bleaching_categories_sql = ", ".join(f"'{name}'" for name in BLEACHING_CATEGORIES)

# SU columns pulled from the `bleaching_percents` CTE built by bleaching_su_sql
bleaching_su_columns_sql = f"""
    bleaching_percents.percent_bleached->'{BLEACHING_CATEGORY_HARD_CORAL}' AS percent_bleached_hard_coral,
    bleaching_percents.percent_bleached->'{BLEACHING_CATEGORY_SOFT_CORAL}' AS percent_bleached_soft_coral,
    bleaching_percents.percent_bleached->'Total coral' AS percent_bleached_total_coral
"""


def bleaching_su_sql(obs_table, weight):
    """
    SU-level bleaching CTEs ending in `bleaching_percents` (pseudosu_id, percent_bleached jsonb keyed by
    coral type). `obs_table` must have pseudosu_id, benthic_category, include_bleaching and
    bleaching_status_val columns; `weight` is the SQL expression each observation contributes.
    """
    return f"""
    bleaching_obs AS (
        SELECT pseudosu_id,
        benthic_category AS coral_type,
        bleaching_status_val,
        {weight} AS weight
        FROM {obs_table}
        WHERE include_bleaching IS TRUE
        AND benthic_category IN ({bleaching_categories_sql})
        AND bleaching_status_val IS NOT NULL
        UNION ALL
        SELECT pseudosu_id,
        'Total coral' AS coral_type,
        bleaching_status_val,
        {weight} AS weight
        FROM {obs_table}
        WHERE include_bleaching IS TRUE
        AND benthic_category IN ({bleaching_categories_sql})
        AND bleaching_status_val IS NOT NULL
    ),
    bleaching_totals AS (
        SELECT pseudosu_id,
        coral_type,
        SUM(weight) AS total_weight,
        COALESCE(SUM(weight) FILTER (WHERE bleaching_status_val > 0), 0) AS bleached_weight
        FROM bleaching_obs
        GROUP BY pseudosu_id, coral_type
    ),
    bleaching_status_weights AS (
        SELECT pseudosu_id,
        coral_type,
        bleaching_status_val,
        SUM(weight) AS status_weight
        FROM bleaching_obs
        GROUP BY pseudosu_id, coral_type, bleaching_status_val
    ),
    bleaching_percents AS (
        SELECT coral_percents.pseudosu_id,
        jsonb_object_agg(coral_percents.coral_type, coral_percents.percents) AS percent_bleached
        FROM (
            SELECT bt.pseudosu_id,
            bt.coral_type,
            jsonb_build_object('Bleached', ROUND(100.0 * bt.bleached_weight / NULLIF(bt.total_weight, 0), 2))
            || jsonb_object_agg(
                bs.name,
                ROUND(100.0 * COALESCE(bsw.status_weight, 0) / NULLIF(bt.total_weight, 0), 2)
            ) AS percents
            FROM bleaching_totals bt
            CROSS JOIN {bleaching_status_sql}
            LEFT JOIN bleaching_status_weights bsw ON (
                bt.pseudosu_id = bsw.pseudosu_id AND
                bt.coral_type = bsw.coral_type AND
                bs.val = bsw.bleaching_status_val
            )
            WHERE bs.val > 0
            GROUP BY bt.pseudosu_id, bt.coral_type, bt.bleached_weight, bt.total_weight
        ) coral_percents
        GROUP BY coral_percents.pseudosu_id
    )
    """


def bleaching_se_sql(su_table):
    """
    SE-level bleaching CTEs ending in `se_bleaching` (sample_event_id, avg/sd jsonb per coral type),
    aggregated from the percent_bleached_* columns of `su_table`.
    """
    return f"""
    bleaching_su AS (
        SELECT sample_event_id, '{BLEACHING_CATEGORY_HARD_CORAL}' AS coral_type, bdata.key, bdata.value
        FROM {su_table}, jsonb_each_text(percent_bleached_hard_coral) AS bdata
        UNION ALL
        SELECT sample_event_id, '{BLEACHING_CATEGORY_SOFT_CORAL}' AS coral_type, bdata.key, bdata.value
        FROM {su_table}, jsonb_each_text(percent_bleached_soft_coral) AS bdata
        UNION ALL
        SELECT sample_event_id, 'Total coral' AS coral_type, bdata.key, bdata.value
        FROM {su_table}, jsonb_each_text(percent_bleached_total_coral) AS bdata
    ),
    se_bleaching AS (
        SELECT sample_event_id,
        jsonb_object_agg(key, ROUND(percent_avg :: numeric, 2)) FILTER (WHERE coral_type = '{BLEACHING_CATEGORY_HARD_CORAL}') AS percent_bleached_hard_coral_avg,
        jsonb_object_agg(key, ROUND(percent_sd :: numeric, 2)) FILTER (WHERE coral_type = '{BLEACHING_CATEGORY_HARD_CORAL}') AS percent_bleached_hard_coral_sd,
        jsonb_object_agg(key, ROUND(percent_avg :: numeric, 2)) FILTER (WHERE coral_type = '{BLEACHING_CATEGORY_SOFT_CORAL}') AS percent_bleached_soft_coral_avg,
        jsonb_object_agg(key, ROUND(percent_sd :: numeric, 2)) FILTER (WHERE coral_type = '{BLEACHING_CATEGORY_SOFT_CORAL}') AS percent_bleached_soft_coral_sd,
        jsonb_object_agg(key, ROUND(percent_avg :: numeric, 2)) FILTER (WHERE coral_type = 'Total coral') AS percent_bleached_total_coral_avg,
        jsonb_object_agg(key, ROUND(percent_sd :: numeric, 2)) FILTER (WHERE coral_type = 'Total coral') AS percent_bleached_total_coral_sd
        FROM (
            SELECT sample_event_id,
            coral_type,
            key,
            AVG(value :: float) AS percent_avg,
            STDDEV(value :: float) AS percent_sd
            FROM bleaching_su
            GROUP BY sample_event_id, coral_type, key
        ) AS bleaching_su_stats
        GROUP BY sample_event_id
    )
    """


sample_event_sql_template = """
    WITH tags AS MATERIALIZED (
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
    project_admins AS MATERIALIZED (
        SELECT 
        project_id,
        jsonb_agg(jsonb_build_object(
            'id', p.id,
            'name',
            (COALESCE(p.first_name, ''::character varying)::text || ' '::text)
            || COALESCE(p.last_name, ''::character varying)::text)
        ) AS project_admins
        FROM project_profile pp
        INNER JOIN profile p ON (pp.profile_id = p.id)
        WHERE project_id = '%(project_id)s'::uuid
        AND role >= 90
        GROUP BY project_id
    ),
    parties AS MATERIALIZED (
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
    )
    SELECT
        project.id AS project_id,
        project.name AS project_name,
        project.status AS project_status,
        project.notes AS project_notes,
        project.includes_gfcr AS project_includes_gfcr,
        project.user_citation,
        'https://datamermaid.org/contact-project?project_id=' :: text ||
            COALESCE(project.id :: text, '' :: text) AS contact_link,
        project_admins.project_admins,
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
        CASE
            WHEN project.data_policy_benthicpqt = 10 THEN 'private' :: text
            WHEN project.data_policy_benthicpqt = 50 THEN 'public summary' :: text
            WHEN project.data_policy_benthicpqt = 100 THEN 'public' :: text
            ELSE '' :: text
        END AS data_policy_benthicpqt,
        CASE
            WHEN project.data_policy_macroinvertebrate = 10 THEN 'private' :: text
            WHEN project.data_policy_macroinvertebrate = 50 THEN 'public summary' :: text
            WHEN project.data_policy_macroinvertebrate = 100 THEN 'public' :: text
            ELSE '' :: text
        END AS data_policy_macroinvertebrate
    FROM
        sample_event se
        JOIN site ON se.site_id = site.id
        JOIN project ON site.project_id = project.id
        LEFT JOIN project_admins ON (project.id = project_admins.project_id)
        LEFT JOIN tags ON project.id = tags.id
        JOIN country ON site.country_id = country.id
        LEFT JOIN api_reeftype rt ON site.reef_type_id = rt.id
        LEFT JOIN api_reefzone rz ON site.reef_zone_id = rz.id
        LEFT JOIN api_reefexposure re ON site.exposure_id = re.id
        JOIN management m ON se.management_id = m.id
        LEFT JOIN management_compliance mc ON m.compliance_id = mc.id
        LEFT JOIN parties ON m.id = parties.management_id
    WHERE
        <<__sql_table_args__>>
"""


class BaseSQLModel(models.Model):
    se_fields = [
        "project_id",
        "project_name",
        "project_status",
        "project_notes",
        "project_includes_gfcr",
        "user_citation",
        "project_admins",
        "contact_link",
        "tags",
        "site_id",
        "site_name",
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
        ROUND(STDDEV("depth"), 2) as depth_sd,
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
    project_includes_gfcr = models.BooleanField(default=False)
    user_citation = models.TextField(blank=True)
    project_admins = models.JSONField(null=True, blank=True)
    contact_link = models.CharField(max_length=255)
    tags = models.JSONField(null=True, blank=True)
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
    management_est_year = models.PositiveSmallIntegerField(null=True, blank=True)
    management_size = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        verbose_name=_("Size (ha)"),
        null=True,
        blank=True,
    )
    management_parties = models.JSONField(null=True, blank=True)
    management_compliance = models.CharField(max_length=100, null=True, blank=True)
    management_rules = models.JSONField(null=True, blank=True)
    management_notes = models.TextField(blank=True)
    sample_date = models.DateField()
    sample_event_id = models.UUIDField()
    sample_event_notes = models.TextField(blank=True)

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
        "su.sample_event_id",
        "su.depth",
        "su.quadrat_size",
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
        v.name AS visibility_name,
        su.notes AS sample_unit_notes
    """

    # SU aggregation SQL common to all SU-level views
    su_aggfields_sql = """
        string_agg(DISTINCT label::text, ', '::text ORDER BY (label::text)) AS label,
        string_agg(DISTINCT relative_depth::text, ', '::text ORDER BY (relative_depth::text)) AS relative_depth,
        string_agg(DISTINCT sample_time::text, ', '::text ORDER BY (sample_time::text)) AS sample_time,
        string_agg(DISTINCT current_name::text, ', '::text ORDER BY (current_name::text)) AS current_name,
        string_agg(DISTINCT tide_name::text, ', '::text ORDER BY (tide_name::text)) AS tide_name,
        string_agg(DISTINCT visibility_name::text, ', '::text ORDER BY (visibility_name::text)) AS visibility_name,
        string_agg(DISTINCT sample_unit_notes::text, '\n\n '::text) AS sample_unit_notes
    """

    # Fields common to all SUs that are actually SU properties (that make SUs distinct)
    depth = models.DecimalField(max_digits=3, decimal_places=1, verbose_name=_("depth (m)"))
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
        "sample_unit_notes",
    ]

    class Meta:
        abstract = True
