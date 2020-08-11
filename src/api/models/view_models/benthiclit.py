from django.utils.translation import ugettext_lazy as _
from ..base import ExtendedManager
from .base import *


class BenthicLITObsView(BaseSUViewModel):
    sql = """
CREATE OR REPLACE VIEW public.vw_benthiclit_obs
 AS
 SELECT o.id,
    {se_fields},
    {su_fields},
    se.data_policy_benthiclit,
    tt.transectmethod_ptr_id AS sample_unit_id,
    tm.sample_time,
    r.name AS relative_depth,
    tm.number AS transect_number,
    tm.label,
    tm.len_surveyed AS transect_len_surveyed,
    rs.name AS reef_slope,
    o.length,
    cat.name AS benthic_category,
    b.name AS benthic_attribute,
    gf.name AS growth_form,
    o.notes AS observation_notes
   FROM obs_benthiclit o
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
     JOIN benthic_attribute cat ON category.root = cat.id
     JOIN benthic_attribute b ON o.attribute_id = b.id
     LEFT JOIN growth_form gf ON o.growth_form_id = gf.id
     JOIN transectmethod_benthiclit tt ON o.benthiclit_id = tt.transectmethod_ptr_id
     JOIN transect_benthic tm ON tt.transect_id = tm.id
     LEFT JOIN api_current c ON tm.current_id = c.id
     LEFT JOIN api_tide t ON tm.tide_id = t.id
     LEFT JOIN api_visibility v ON tm.visibility_id = v.id
     LEFT JOIN api_relativedepth r ON tm.relative_depth_id = r.id
     LEFT JOIN api_reefslope rs ON tm.reef_slope_id = rs.id
     JOIN ( SELECT tt_1.transect_id,
            jsonb_agg(jsonb_build_object('id', p.id, 'name', (COALESCE(p.first_name, ''::character varying)::text || 
            ' '::text) || COALESCE(p.last_name, ''::character varying)::text)) AS observers
           FROM observer o1
             JOIN profile p ON o1.profile_id = p.id
             JOIN transectmethod tm ON o1.transectmethod_id = tm.id
             JOIN transectmethod_benthiclit tt_1 ON tm.id = tt_1.transectmethod_ptr_id
          GROUP BY tt_1.transect_id) observers ON tm.id = observers.transect_id
     JOIN vw_sample_events se ON tm.sample_event_id = se.sample_event_id;
    """.format(
        se_fields=", ".join([f"se.{f}" for f in BaseSUViewModel.se_fields]),
        su_fields=BaseSUViewModel.su_fields_sql,
    )

    reverse_sql = "DROP VIEW IF EXISTS public.vw_benthiclit_obs CASCADE;"

    sample_unit_id = models.UUIDField()
    sample_time = models.TimeField()
    transect_number = models.PositiveSmallIntegerField()
    label = models.CharField(max_length=50, blank=True)
    transect_len_surveyed = models.PositiveSmallIntegerField(
        verbose_name=_("transect length surveyed (m)")
    )
    reef_slope = models.CharField(max_length=50)
    length = models.PositiveSmallIntegerField()
    benthic_category = models.CharField(max_length=100)
    benthic_attribute = models.CharField(max_length=100)
    growth_form = models.CharField(max_length=100)
    observation_notes = models.TextField(blank=True)
    data_policy_benthiclit = models.CharField(max_length=50)

    class Meta:
        db_table = "vw_benthiclit_obs"
        managed = False


class BenthicLITSUView(BaseSUViewModel):
    project_lookup = "project_id"

    cat_totals_join = " AND ".join([
        f"cps.{f} = cat_totals.{f}" for f in
        BaseSUViewModel.se_fields +
        BaseSUViewModel.su_fields
    ])

    cat_percents_join = " AND ".join([
        f"su.{f} = cat_percents.{f}" for f in
        BaseSUViewModel.se_fields +
        BaseSUViewModel.su_fields
    ])

    sql = """
CREATE OR REPLACE VIEW public.vw_benthiclit_su
 AS
SELECT NULL AS id, 
{su_fields_all},
su.data_policy_benthiclit,
su.transect_number, su.transect_len_surveyed, su.reef_slope,
percent_cover_by_benthic_category
FROM (
    SELECT  
    {se_fields},
    {su_fields}, 
    data_policy_benthiclit,
    transect_number, transect_len_surveyed, reef_slope
    FROM vw_benthiclit_obs obs
    GROUP BY  
    {se_fields},
    {su_fields}, 
    data_policy_benthiclit,
    transect_number, transect_len_surveyed, reef_slope
) su
INNER JOIN (
    WITH cps AS (
        SELECT 
        {se_fields},
        {su_fields}, 
        benthic_category,
        SUM(length) AS category_length
        FROM vw_benthiclit_obs
        GROUP BY 
        {se_fields},
        {su_fields}, 
        benthic_category
    )
    SELECT {cps_fields},
    jsonb_object_agg(
        cps.benthic_category, 
        ROUND(100 * cps.category_length / cat_totals.su_length, 2)
    ) AS percent_cover_by_benthic_category
    FROM cps
    INNER JOIN (
        SELECT 
        {se_fields},
        {su_fields}, 
        SUM(category_length) AS su_length
        FROM cps
        GROUP BY 
        {se_fields},
        {su_fields}
    ) cat_totals ON (
        {cat_totals_join}
    )
    GROUP BY {cps_fields}
) cat_percents ON (
    {cat_percents_join}
)
    """.format(
        se_fields=", ".join(BaseSUViewModel.se_fields),
        su_fields=", ".join(BaseSUViewModel.su_fields),
        su_fields_all=", ".join([f"su.{f}" for f in BaseSUViewModel.se_fields + BaseSUViewModel.su_fields]),
        cps_fields=", ".join([f"cps.{f}" for f in BaseSUViewModel.se_fields + BaseSUViewModel.su_fields]),
        cat_totals_join=cat_totals_join,
        cat_percents_join=cat_percents_join
    )

    reverse_sql = "DROP VIEW IF EXISTS public.vw_benthiclit_su CASCADE;"

    transect_number = models.PositiveSmallIntegerField()
    transect_len_surveyed = models.PositiveSmallIntegerField(
        verbose_name=_("transect length surveyed (m)")
    )
    reef_slope = models.CharField(max_length=50)
    percent_cover_by_benthic_category = JSONField(null=True, blank=True)
    data_policy_benthiclit = models.CharField(max_length=50)

    objects = ExtendedManager()

    class Meta:
        db_table = "vw_benthiclit_su"
        managed = False


class BenthicLITSEView(BaseViewModel):
    project_lookup = "project_id"

    sql = """
CREATE OR REPLACE VIEW public.vw_benthiclit_se
 AS
SELECT 
vw_benthiclit_su.sample_event_id AS id,
{se_fields},
data_policy_benthiclit, 
string_agg(DISTINCT current_name, ', ' ORDER BY current_name) AS current_name,
string_agg(DISTINCT tide_name, ', ' ORDER BY tide_name) AS tide_name,
string_agg(DISTINCT visibility_name, ', ' ORDER BY visibility_name) AS visibility_name,
COUNT(vw_benthiclit_su.id) AS sample_unit_count,
ROUND(AVG("depth"), 2) as depth_avg,
percent_cover_by_benthic_category_avg

FROM vw_benthiclit_su

INNER JOIN (
    SELECT sample_event_id, 
    jsonb_object_agg(cat, ROUND(cat_percent::numeric, 2)) AS percent_cover_by_benthic_category_avg
    FROM (
        SELECT sample_event_id, 
        cpdata.key AS cat, 
        AVG(cpdata.value::float) AS cat_percent
        FROM public.vw_benthiclit_su,
        jsonb_each_text(percent_cover_by_benthic_category) AS cpdata
        GROUP BY sample_event_id, cpdata.key
    ) AS benthiclit_su_cp
    GROUP BY sample_event_id
) AS benthiclit_se_cat_percents
ON vw_benthiclit_su.sample_event_id = benthiclit_se_cat_percents.sample_event_id

GROUP BY 
{se_fields},
data_policy_benthiclit,
percent_cover_by_benthic_category_avg
    """.format(
        se_fields=", ".join([f"vw_benthiclit_su.{f}" for f in BaseViewModel.se_fields]),
    )

    reverse_sql = "DROP VIEW IF EXISTS public.vw_benthiclit_se CASCADE;"

    sample_unit_count = models.PositiveSmallIntegerField()
    depth_avg = models.DecimalField(
        max_digits=4, decimal_places=2, verbose_name=_("depth (m)")
    )
    percent_cover_by_benthic_category_avg = JSONField(null=True, blank=True)
    data_policy_benthiclit = models.CharField(max_length=50)

    objects = ExtendedManager()

    class Meta:
        db_table = "vw_benthiclit_se"
        managed = False
