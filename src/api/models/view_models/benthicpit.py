from django.utils.translation import ugettext_lazy as _
from ..base import ExtendedManager
from .base import *


class BenthicPITObsView(BaseViewModel):
    sql = """
CREATE OR REPLACE VIEW public.vw_benthicpit_obs
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
    se.data_policy_benthicpit,
    observers.observers, 
    tt.transectmethod_ptr_id AS sample_unit_id,
    tb.number AS transect_number,
    tb.label,
    tb.len_surveyed AS transect_len_surveyed,
    rs.name AS reef_slope,
    tt.interval_size,
    tt.interval_start,
    o."interval",
    c.name AS benthic_category,
    b.name AS benthic_attribute,
    gf.name AS growth_form,
    o.notes AS observation_notes
   FROM obs_benthicpit o
     JOIN ( WITH RECURSIVE tree(child, root) AS (
                 SELECT c_1.id,
                    c_1.id
                   FROM benthic_attribute c_1
                     LEFT JOIN benthic_attribute p ON c_1.parent_id = p.id
                  WHERE p.id IS NULL
                UNION
                 SELECT benthic_attribute.id,
                    tree_1.root
                   FROM tree tree_1
                     JOIN benthic_attribute ON tree_1.child = benthic_attribute.parent_id
                )
         SELECT tree.child,
            tree.root
           FROM tree) category ON o.attribute_id = category.child
     JOIN benthic_attribute c ON category.root = c.id
     JOIN benthic_attribute b ON o.attribute_id = b.id
     LEFT JOIN growth_form gf ON o.growth_form_id = gf.id
     JOIN transectmethod_benthicpit tt ON o.benthicpit_id = tt.transectmethod_ptr_id
     JOIN transect_benthic tb ON tt.transect_id = tb.id
     LEFT JOIN api_reefslope rs ON tb.reef_slope_id = rs.id
     JOIN ( SELECT tt_1.transect_id,
            jsonb_agg(jsonb_build_object('id', p.id, 'name', (COALESCE(p.first_name, ''::character varying)::text || 
            ' '::text) || COALESCE(p.last_name, ''::character varying)::text)) AS observers
           FROM observer o1
             JOIN profile p ON o1.profile_id = p.id
             JOIN transectmethod tm ON o1.transectmethod_id = tm.id
             JOIN transectmethod_benthicpit tt_1 ON tm.id = tt_1.transectmethod_ptr_id
          GROUP BY tt_1.transect_id) observers ON tb.id = observers.transect_id
     JOIN vw_sample_events se ON tb.sample_event_id = se.sample_event_id;
    """.format(
        se_fields=", ".join([f"se.{f}" for f in BaseViewModel.se_fields])
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
    depth = models.DecimalField(
        max_digits=3, decimal_places=1, verbose_name=_("depth (m)")
    )
    reef_slope = models.CharField(max_length=50)
    interval_size = models.DecimalField(
        max_digits=4, decimal_places=2, default=0.5, verbose_name=_("interval size (m)")
    )
    interval_start = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0.5,
        verbose_name=_("interval start (m)"),
    )
    interval = models.DecimalField(max_digits=7, decimal_places=2)
    benthic_category = models.CharField(max_length=100)
    benthic_attribute = models.CharField(max_length=100)
    growth_form = models.CharField(max_length=100)
    observation_notes = models.TextField(blank=True)
    data_policy_benthicpit = models.CharField(max_length=50)

    class Meta:
        db_table = "vw_benthicpit_obs"
        managed = False


class BenthicPITSUView(BaseViewModel):
    project_lookup = "project_id"

    sql = """
CREATE OR REPLACE VIEW public.vw_benthicpit_su
 AS
SELECT
su.sample_unit_id AS id, {se_fields},
current_name, tide_name, visibility_name, data_policy_benthicpit,
transect_number, transect_len_surveyed, observers,
reef_slope, interval_size, interval_start,
percent_avgs
FROM (
    SELECT 
    sample_unit_id, {se_fields},
    current_name, tide_name, visibility_name, data_policy_benthicpit,
    transect_number, transect_len_surveyed, observers,
    reef_slope, interval_size, interval_start
    FROM vw_benthicpit_obs obs
    GROUP BY 
    sample_unit_id, {se_fields},
    current_name, tide_name, visibility_name, data_policy_benthicpit,
    transect_number, transect_len_surveyed, "depth", observers,
    reef_slope, interval_size, interval_start
) su
INNER JOIN (
    WITH cps AS (
        SELECT 
        sample_unit_id,
        benthic_category,
        SUM(interval_size) AS category_length
        FROM vw_benthicpit_obs
        GROUP BY sample_unit_id, benthic_category
    )
    SELECT
    cps.sample_unit_id,
    jsonb_object_agg(
        cps.benthic_category, 
        ROUND(100 * cps.category_length / cat_totals.su_length, 2)
    ) AS percent_avgs
    FROM cps
    INNER JOIN (
        SELECT 
        sample_unit_id,
        SUM(category_length) AS su_length
        FROM cps
        GROUP BY sample_unit_id
    ) cat_totals ON (cps.sample_unit_id = cat_totals.sample_unit_id)
    GROUP BY cps.sample_unit_id
) cat_percents ON (su.sample_unit_id = cat_percents.sample_unit_id)
    """.format(
        se_fields=", ".join(BaseViewModel.se_fields)
    )

    observers = JSONField(null=True, blank=True)
    transect_number = models.PositiveSmallIntegerField()
    transect_len_surveyed = models.PositiveSmallIntegerField(
        verbose_name=_("transect length surveyed (m)")
    )
    depth = models.DecimalField(
        max_digits=3, decimal_places=1, verbose_name=_("depth (m)")
    )
    reef_slope = models.CharField(max_length=50)
    interval_size = models.DecimalField(
        max_digits=4, decimal_places=2, default=0.5, verbose_name=_("interval size (m)")
    )
    interval_start = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0.5,
        verbose_name=_("interval start (m)"),
    )
    percent_avgs = JSONField(null=True, blank=True)
    data_policy_benthicpit = models.CharField(max_length=50)

    objects = ExtendedManager()

    class Meta:
        db_table = "vw_benthicpit_su"
        managed = False


class BenthicPITSEView(BaseViewModel):
    project_lookup = "project_id"

    sql = """
CREATE OR REPLACE VIEW public.vw_benthicpit_se
 AS
SELECT 
NULL AS id,
vw_benthicpit_su.project_id, project_name, project_status, project_notes, contact_link, tags, 
vw_benthicpit_su.site_id, site_name, location, site_notes, country_id, country_name, reef_type, reef_zone, 
reef_exposure, vw_benthicpit_su.management_id, management_name, management_name_secondary, management_est_year, 
management_size, management_parties, management_compliance, management_rules, management_notes, 
vw_benthicpit_su.sample_date, 
data_policy_benthicpit, 
string_agg(DISTINCT current_name, ', ' ORDER BY current_name) AS current_name,
string_agg(DISTINCT tide_name, ', ' ORDER BY tide_name) AS tide_name,
string_agg(DISTINCT visibility_name, ', ' ORDER BY visibility_name) AS visibility_name,
COUNT(vw_benthicpit_su.id) AS sample_unit_count,
ROUND(AVG("depth"), 2) as depth_avg,
benthicpit_by_cat_avg

FROM public.vw_benthicpit_su

INNER JOIN (
    SELECT project_id, site_id, management_id, sample_date, 
    jsonb_object_agg(cat, ROUND(cat_percent::numeric, 2)) AS benthicpit_by_cat_avg
    FROM (
        SELECT project_id, site_id, management_id, sample_date, 
        cpdata.key AS cat, AVG(cpdata.value::float) AS cat_percent
        FROM public.vw_benthicpit_su,
        jsonb_each_text(percent_avgs) AS cpdata
        GROUP BY 
        project_id, site_id, management_id, sample_date, cpdata.key
    ) AS benthicpit_su_cp
    GROUP BY project_id, site_id, management_id, sample_date
) AS benthicpit_se_cat_percents
ON (
    vw_benthicpit_su.project_id = benthicpit_se_cat_percents.project_id
    AND vw_benthicpit_su.site_id = benthicpit_se_cat_percents.site_id
    AND vw_benthicpit_su.management_id = benthicpit_se_cat_percents.management_id
    AND vw_benthicpit_su.sample_date = benthicpit_se_cat_percents.sample_date
)

GROUP BY 
vw_benthicpit_su.project_id, project_name, project_status, project_notes, contact_link, tags, 
vw_benthicpit_su.site_id, site_name, location, site_notes, country_id, country_name, reef_type, reef_zone, 
reef_exposure, vw_benthicpit_su.management_id, management_name, management_name_secondary, management_est_year, 
management_size, management_parties, management_compliance, management_rules, management_notes, 
vw_benthicpit_su.sample_date, 
data_policy_benthicpit,
benthicpit_by_cat_avg
    """

    sample_unit_count = models.PositiveSmallIntegerField()
    depth_avg = models.DecimalField(
        max_digits=4, decimal_places=2, verbose_name=_("depth (m)")
    )
    benthicpit_by_cat_avg = JSONField(null=True, blank=True)
    data_policy_benthicpit = models.CharField(max_length=50)

    objects = ExtendedManager()

    class Meta:
        db_table = "vw_benthicpit_se"
        managed = False
