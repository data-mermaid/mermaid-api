from django.contrib.gis.db import models

from sqltables import SQLTableArg, SQLTableManager
from . import Project
from .sql_models import (
    BeltFishSUSQLModel,
    BenthicLITSUSQLModel,
    BenthicPITSUSQLModel,
    BenthicPhotoQuadratTransectSUSQLModel,
    BleachingQCSUSQLModel,
    HabitatComplexitySUSQLModel,
)


class SummarySampleEventBaseModel(models.Model):
    sample_event_id = models.UUIDField(primary_key=True)
    id = models.UUIDField(blank=True, null=True)
    site_id = models.UUIDField()
    site_name = models.CharField(max_length=255)
    site_notes = models.TextField(blank=True)
    location = models.PointField(srid=4326)
    project_id = models.UUIDField()
    project_name = models.CharField(max_length=255)
    project_status = models.PositiveSmallIntegerField(
        choices=Project.STATUSES, default=Project.OPEN
    )
    project_notes = models.TextField(blank=True)
    sample_event_notes = models.TextField(blank=True, null=True)
    contact_link = models.CharField(max_length=255)
    tags = models.JSONField(null=True, blank=True)
    country_id = models.UUIDField()
    country_name = models.CharField(max_length=50)
    reef_type = models.CharField(max_length=50)
    reef_zone = models.CharField(max_length=50)
    reef_exposure = models.CharField(max_length=50)  # name change
    project_admins = models.JSONField(null=True, blank=True)
    sample_date = models.DateField(null=True, blank=True)
    management_id = models.UUIDField()
    management_name = models.CharField(max_length=255)
    management_notes = models.TextField(blank=True, null=True)
    protocols = models.JSONField(null=True, blank=True)  # most keys changed inside here
    data_policy_beltfish = models.CharField(max_length=50)
    data_policy_benthiclit = models.CharField(max_length=50)
    data_policy_benthicpit = models.CharField(max_length=50)
    data_policy_habitatcomplexity = models.CharField(max_length=50)
    data_policy_bleachingqc = models.CharField(max_length=50)
    data_policy_benthicpqt = models.CharField(max_length=50)

    class Meta:
        abstract = True


class SummarySampleEventSQLModel(SummarySampleEventBaseModel):
    sql = f"""
        WITH beltfish_su AS (
            SELECT * FROM summary_belt_fish_su WHERE project_id = '%(project_id)s'::uuid
        ),
        benthiclit_su AS (
            SELECT * FROM summary_benthiclit_su WHERE project_id = '%(project_id)s'::uuid
        ),
        benthicpit_su AS (
            SELECT * FROM summary_benthicpit_su WHERE project_id = '%(project_id)s'::uuid
        ),
        bleachingqc_su AS (
            SELECT * FROM summary_bleachingqc_su WHERE project_id = '%(project_id)s'::uuid
        ),
        benthicpqt_su AS (
            SELECT * FROM summary_benthicpqt_su WHERE project_id = '%(project_id)s'::uuid
        ),
        habitatcomplexity_su AS (
            SELECT * FROM summary_habitatcomplexity_su WHERE project_id = '%(project_id)s'::uuid
        )

        SELECT
        NULL AS id,
        sample_event.id as sample_event_id,
        site.id AS site_id,
        site.name AS site_name,
        site.location,
        site.notes AS site_notes,
        project.id AS project_id,
        project.name AS project_name,
        project.status AS project_status,
        project.notes AS project_notes,
        sample_event.notes AS sample_event_notes,
        'https://datamermaid.org/contact-project?project_id=' || COALESCE(project.id::text, '') AS contact_link,
        country.id AS country_id,
        country.name AS country_name,
        api_reeftype.name AS reef_type,
        api_reefzone.name AS reef_zone,
        api_reefexposure.name AS reef_exposure,
        tags.tags,
        pa.project_admins,
        sample_date,
        m.id AS management_id,
        CASE WHEN m.name_secondary = '' THEN m.name ELSE m.name || ' [' || m.name_secondary || ']' END AS management_name,
        NULLIF(m.notes, '') AS management_notes,
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
        (CASE WHEN project.data_policy_benthicpqt=10 THEN 'private'
            WHEN project.data_policy_benthicpqt=50 THEN 'public summary'
            WHEN project.data_policy_benthicpqt=100 THEN 'public'
            ELSE ''
        END) AS data_policy_benthicpqt,

        jsonb_strip_nulls(jsonb_build_object(
            'beltfish', NULLIF(jsonb_strip_nulls(jsonb_build_object(
                'sample_unit_count', fb.sample_unit_count,
                'biomass_kgha_avg', (CASE WHEN project.data_policy_beltfish < 50 THEN NULL ELSE fb.biomass_kgha_avg END),
                'biomass_kgha_by_trophic_group_avg', (CASE WHEN project.data_policy_beltfish < 50 THEN NULL ELSE
                fbtg.biomass_kgha_by_trophic_group_avg END)
            )), '{{}}'),
            'benthiclit', NULLIF(jsonb_strip_nulls(jsonb_build_object(
                'sample_unit_count', bl.sample_unit_count,
                'percent_cover_by_benthic_category_avg', (CASE WHEN project.data_policy_benthiclit < 50 THEN NULL ELSE
                bl.percent_cover_by_benthic_category_avg END)
            )), '{{}}'),
            'benthicpit', NULLIF(jsonb_strip_nulls(jsonb_build_object(
                'sample_unit_count', bp.sample_unit_count,
                'percent_cover_by_benthic_category_avg', (CASE WHEN project.data_policy_benthicpit < 50 THEN NULL ELSE
                bp.percent_cover_by_benthic_category_avg END)
            )), '{{}}'),
            'benthicpqt', NULLIF(jsonb_strip_nulls(jsonb_build_object(
                'sample_unit_count', pqt.sample_unit_count,
                'percent_cover_by_benthic_category_avg', (CASE WHEN project.data_policy_benthicpqt < 50 THEN NULL ELSE
                pqt.percent_cover_by_benthic_category_avg END)
            )), '{{}}'),
            'habitatcomplexity', NULLIF(jsonb_strip_nulls(jsonb_build_object(
                'sample_unit_count', hc.sample_unit_count,
                'score_avg_avg', (CASE WHEN project.data_policy_habitatcomplexity < 50 THEN NULL ELSE hc.score_avg_avg END)
            )), '{{}}'),
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
            )), '{{}}'),
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
            )), '{{}}')
        )) AS protocols

        FROM sample_event
        INNER JOIN site ON (sample_event.site_id = site.id)
        INNER JOIN management m ON (sample_event.management_id = m.id)
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
            AND project.id = '%(project_id)s'::uuid
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
            AND project.id = '%(project_id)s'::uuid
            GROUP BY project.id
        ) tags ON (project.id = tags.id)

        LEFT JOIN (
            SELECT sample_event_id,
            COUNT(pseudosu_id) AS sample_unit_count,
            ROUND(AVG(biomass_kgha), 1) AS biomass_kgha_avg
            FROM beltfish_su
            GROUP BY sample_event_id
        ) fb ON (sample_event.id = fb.sample_event_id)
        LEFT JOIN (
            SELECT sample_event_id,
            jsonb_object_agg(tg, ROUND(biomass_kgha::numeric, 2)) AS biomass_kgha_by_trophic_group_avg
            FROM (
                SELECT meta_su_tgs.sample_event_id, tg,
                AVG(biomass_kgha) AS biomass_kgha
                FROM (
                    SELECT sample_event_id, pseudosu_id, tgdata.key AS tg,
                    SUM(tgdata.value::double precision) AS biomass_kgha
                    FROM beltfish_su,
                    LATERAL jsonb_each_text(biomass_kgha_by_trophic_group) tgdata(key, value)
                    GROUP BY sample_event_id, pseudosu_id, tgdata.key
                ) meta_su_tgs
                GROUP BY meta_su_tgs.sample_event_id, tg
            ) beltfish_su_tg
            GROUP BY sample_event_id
        ) fbtg ON (sample_event.id = fbtg.sample_event_id)

        LEFT JOIN (
            SELECT benthiclit_su.sample_event_id,
            COUNT(pseudosu_id) AS sample_unit_count,
            percent_cover_by_benthic_category_avg
            FROM benthiclit_su
            INNER JOIN (
                SELECT sample_event_id,
                jsonb_object_agg(cat, ROUND(cat_percent::numeric, 2)) AS percent_cover_by_benthic_category_avg
                FROM (
                    SELECT sample_event_id,
                    cpdata.key AS cat,
                    AVG(cpdata.value::float) AS cat_percent
                    FROM benthiclit_su,
                    jsonb_each_text(percent_cover_by_benthic_category) AS cpdata
                    GROUP BY sample_event_id, cpdata.key
                ) AS benthiclit_su_cp
                GROUP BY sample_event_id
            ) AS benthiclit_se_cat_percents
            ON benthiclit_su.sample_event_id = benthiclit_se_cat_percents.sample_event_id
            GROUP BY
            benthiclit_su.sample_event_id,
            percent_cover_by_benthic_category_avg
        ) bl ON (sample_event.id = bl.sample_event_id)

        LEFT JOIN (
            SELECT benthicpit_su.sample_event_id,
            COUNT(pseudosu_id) AS sample_unit_count,
            percent_cover_by_benthic_category_avg
            FROM benthicpit_su
            INNER JOIN (
                SELECT sample_event_id,
                jsonb_object_agg(cat, ROUND(cat_percent::numeric, 2)) AS percent_cover_by_benthic_category_avg
                FROM (
                    SELECT sample_event_id,
                    cpdata.key AS cat,
                    AVG(cpdata.value::float) AS cat_percent
                    FROM benthicpit_su,
                    jsonb_each_text(percent_cover_by_benthic_category) AS cpdata
                    GROUP BY sample_event_id, cpdata.key
                ) AS benthicpit_su_cp
                GROUP BY sample_event_id
            ) AS benthicpit_se_cat_percents
            ON benthicpit_su.sample_event_id = benthicpit_se_cat_percents.sample_event_id
            GROUP BY
            benthicpit_su.sample_event_id,
            percent_cover_by_benthic_category_avg
        ) bp ON (sample_event.id = bp.sample_event_id)

        LEFT JOIN (
            SELECT benthicpqt_su.sample_event_id,
            COUNT(pseudosu_id) AS sample_unit_count,
            percent_cover_by_benthic_category_avg
            FROM benthicpqt_su
            INNER JOIN (
                SELECT sample_event_id,
                jsonb_object_agg(cat, ROUND(cat_percent::numeric, 2)) AS percent_cover_by_benthic_category_avg
                FROM (
                    SELECT sample_event_id,
                    cpdata.key AS cat,
                    AVG(cpdata.value::float) AS cat_percent
                    FROM benthicpqt_su,
                    jsonb_each_text(percent_cover_by_benthic_category) AS cpdata
                    GROUP BY sample_event_id, cpdata.key
                ) AS benthicpqt_su_cp
                GROUP BY sample_event_id
            ) AS benthicpqt_se_cat_percents
            ON benthicpqt_su.sample_event_id = benthicpqt_se_cat_percents.sample_event_id
            GROUP BY
            benthicpqt_su.sample_event_id,
            percent_cover_by_benthic_category_avg
        ) pqt ON (sample_event.id = pqt.sample_event_id)

        LEFT JOIN (
            SELECT sample_event_id,
            COUNT(pseudosu_id) AS sample_unit_count,
            ROUND(AVG(score_avg), 2) AS score_avg_avg
            FROM habitatcomplexity_su
            GROUP BY
            sample_event_id
        ) hc ON (sample_event.id = hc.sample_event_id)

        LEFT JOIN (
            SELECT sample_event_id, 
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
            FROM bleachingqc_su
            GROUP BY
            sample_event_id
        ) bleachingqc ON (sample_event.id = bleachingqc.sample_event_id)

        WHERE site.project_id = '%(project_id)s'::uuid
    """

    class Meta:
        db_table = "summary_sample_event_sql"
        managed = False
        app_label = "api"

    objects = SQLTableManager()
    sql_args = dict(project_id=SQLTableArg(required=True))


class SummarySampleEventModel(SummarySampleEventBaseModel):
    class Meta:
        db_table = "summary_sample_event"
