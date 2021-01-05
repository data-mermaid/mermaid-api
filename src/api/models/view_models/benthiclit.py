from django.utils.translation import ugettext_lazy as _
from ..base import ExtendedManager
from .base import *


class BenthicLITObsView(BaseSUViewModel):
    # Unique combination of these fields defines a single (pseudo) sample unit. All other fields are aggregated.
    su_fields = BaseSUViewModel.se_fields + [
        "depth",
        "transect_number",
        "transect_len_surveyed",
        "data_policy_benthiclit",
    ]

    sql = """
CREATE OR REPLACE VIEW public.vw_benthiclit_obs
 AS
WITH benthiclit_obs AS (
 SELECT o.id,
    {se_fields},
    {su_fields},
    se.data_policy_benthiclit,
    su.number AS transect_number,
    su.len_surveyed AS transect_len_surveyed,
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
     JOIN transect_benthic su ON tt.transect_id = su.id
     LEFT JOIN api_current c ON su.current_id = c.id
     LEFT JOIN api_tide t ON su.tide_id = t.id
     LEFT JOIN api_visibility v ON su.visibility_id = v.id
     LEFT JOIN api_relativedepth r ON su.relative_depth_id = r.id
     LEFT JOIN api_reefslope rs ON su.reef_slope_id = rs.id
     JOIN ( SELECT tt_1.transect_id,
            jsonb_agg(jsonb_build_object('id', p.id, 'name', (COALESCE(p.first_name, ''::character varying)::text || 
            ' '::text) || COALESCE(p.last_name, ''::character varying)::text)) AS observers
           FROM observer o1
             JOIN profile p ON o1.profile_id = p.id
             JOIN transectmethod tm ON o1.transectmethod_id = tm.id
             JOIN transectmethod_benthiclit tt_1 ON tm.id = tt_1.transectmethod_ptr_id
          GROUP BY tt_1.transect_id) observers ON su.id = observers.transect_id
     JOIN vw_sample_events se ON su.sample_event_id = se.sample_event_id
)

SELECT benthiclit_obs.*, benthiclit_su.total_length
FROM benthiclit_obs
INNER JOIN (
    SELECT {su_fields_grouping}, 
    SUM(length) AS total_length
    FROM benthiclit_obs
    GROUP BY {su_fields_grouping}
) benthiclit_su
ON ({su_fields_join});
    """.format(
        se_fields=", ".join([f"se.{f}" for f in BaseSUViewModel.se_fields]),
        su_fields=BaseSUViewModel.su_fields_sql,
        su_fields_grouping=", ".join(su_fields),
        su_fields_join=" AND ".join(
            [
                f"(benthiclit_obs.{f} = benthiclit_su.{f} OR (benthiclit_obs.{f} "
                f"IS NULL AND benthiclit_su.{f} IS NULL))"
                for f in su_fields
            ]
        ),
    )

    reverse_sql = "DROP VIEW IF EXISTS public.vw_benthiclit_obs CASCADE;"

    sample_unit_id = models.UUIDField()
    transect_number = models.PositiveSmallIntegerField()
    relative_depth = models.CharField(max_length=50)
    transect_len_surveyed = models.DecimalField(max_digits=4, decimal_places=1, verbose_name=_("transect length surveyed (m)"))
    reef_slope = models.CharField(max_length=50)
    length = models.PositiveSmallIntegerField()
    total_length = models.PositiveIntegerField()
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

    # Unique combination of these fields defines a single (pseudo) sample unit. All other fields are aggregated.
    su_fields = BaseSUViewModel.se_fields + [
        "depth",
        "transect_number",
        "transect_len_surveyed",
        "data_policy_benthiclit",
    ]

    sql = """
CREATE OR REPLACE VIEW public.vw_benthiclit_su
 AS
SELECT NULL AS id, 
benthiclit_su.pseudosu_id,
{su_fields},
{agg_su_fields},
benthiclit_su.total_length,
reef_slope, 
percent_cover_by_benthic_category
FROM (
    SELECT su.pseudosu_id,
    jsonb_agg(DISTINCT su.sample_unit_id) AS sample_unit_ids,
    SUM(vw_benthiclit_obs.length) AS total_length,
    {su_fields_qualified},
    {su_aggfields_sql},
    string_agg(DISTINCT reef_slope::text, ', '::text ORDER BY (reef_slope::text)) AS reef_slope

    FROM vw_benthiclit_obs
    INNER JOIN sample_unit_cache su ON (vw_benthiclit_obs.sample_unit_id = su.sample_unit_id)
    GROUP BY su.pseudosu_id,
    {su_fields_qualified}
) benthiclit_su

INNER JOIN (
    WITH cps AS (
        SELECT su.pseudosu_id, 
        benthic_category,
        SUM(length) AS category_length
        FROM vw_benthiclit_obs
        INNER JOIN sample_unit_cache su ON (vw_benthiclit_obs.sample_unit_id = su.sample_unit_id)
        GROUP BY su.pseudosu_id, 
        benthic_category
    )
    SELECT cps.pseudosu_id, 
    jsonb_object_agg(
        cps.benthic_category, 
        ROUND(100 * cps.category_length / cat_totals.su_length, 2)
    ) AS percent_cover_by_benthic_category
    FROM cps
    INNER JOIN (
        SELECT pseudosu_id, 
        SUM(category_length) AS su_length
        FROM cps
        GROUP BY pseudosu_id
    ) cat_totals ON (cps.pseudosu_id = cat_totals.pseudosu_id)
    GROUP BY cps.pseudosu_id
) cat_percents 
ON (benthiclit_su.pseudosu_id = cat_percents.pseudosu_id)

INNER JOIN (
    SELECT pseudosu_id,
    jsonb_agg(DISTINCT observer) AS observers

    FROM (
        SELECT su.pseudosu_id,
        jsonb_array_elements(observers) AS observer
        FROM vw_benthiclit_obs
        INNER JOIN sample_unit_cache su ON (vw_benthiclit_obs.sample_unit_id = su.sample_unit_id)
        GROUP BY su.pseudosu_id, 
        observers
    ) benthiclit_obs_obs
    GROUP BY pseudosu_id
) benthiclit_obs
ON (benthiclit_su.pseudosu_id = benthiclit_obs.pseudosu_id);
    """.format(
        su_fields=", ".join(su_fields),
        su_fields_qualified=", ".join([f"vw_benthiclit_obs.{f}" for f in su_fields]),
        agg_su_fields=", ".join(BaseSUViewModel.agg_su_fields),
        su_aggfields_sql=BaseSUViewModel.su_aggfields_sql,
    )

    reverse_sql = "DROP VIEW IF EXISTS public.vw_benthiclit_su CASCADE;"

    sample_unit_ids = JSONField()
    transect_number = models.PositiveSmallIntegerField()
    transect_len_surveyed = models.DecimalField(max_digits=4, decimal_places=1, verbose_name=_("transect length surveyed (m)"))
    total_length = models.PositiveIntegerField()
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
SELECT vw_benthiclit_su.sample_event_id AS id,
{se_fields},
data_policy_benthiclit, 
{su_aggfields_sql},
COUNT(vw_benthiclit_su.pseudosu_id) AS sample_unit_count,
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
percent_cover_by_benthic_category_avg;
    """.format(
        se_fields=", ".join([f"vw_benthiclit_su.{f}" for f in BaseViewModel.se_fields]),
        su_aggfields_sql=BaseViewModel.su_aggfields_sql,
    )

    reverse_sql = "DROP VIEW IF EXISTS public.vw_benthiclit_se CASCADE;"

    sample_unit_count = models.PositiveSmallIntegerField()
    depth_avg = models.DecimalField(
        max_digits=4, decimal_places=2, verbose_name=_("depth (m)")
    )
    current_name = models.CharField(max_length=100)
    tide_name = models.CharField(max_length=100)
    visibility_name = models.CharField(max_length=100)
    percent_cover_by_benthic_category_avg = JSONField(null=True, blank=True)
    data_policy_benthiclit = models.CharField(max_length=50)

    objects = ExtendedManager()

    class Meta:
        db_table = "vw_benthiclit_se"
        managed = False
