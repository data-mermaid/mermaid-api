from django.utils.translation import ugettext_lazy as _
from ..base import ExtendedManager
from .base import *


class HabitatComplexityObsView(BaseSUViewModel):
    sql = """
CREATE OR REPLACE VIEW vw_habitatcomplexity_obs AS 
SELECT o.id,
  {se_fields},
  {su_fields},
  se.data_policy_habitatcomplexity,
  su.number AS transect_number,
  su.len_surveyed AS transect_len_surveyed,
  rs.name AS reef_slope,
  tt.interval_size,
  o."interval",
  s.val AS score,
  s.name AS score_name,
  o.notes AS observation_notes
FROM
  obs_habitatcomplexity o
  INNER JOIN api_habitatcomplexityscore s ON (o.score_id = s.id)
  INNER JOIN transectmethod_habitatcomplexity tt ON o.habitatcomplexity_id = tt.transectmethod_ptr_id
  INNER JOIN transect_benthic su ON tt.transect_id = su.id
  LEFT JOIN api_current c ON su.current_id = c.id
  LEFT JOIN api_tide t ON su.tide_id = t.id
  LEFT JOIN api_visibility v ON su.visibility_id = v.id
  LEFT JOIN api_relativedepth r ON su.relative_depth_id = r.id
  LEFT JOIN api_reefslope rs ON su.reef_slope_id = rs.id
  JOIN ( 
      SELECT tt_1.transect_id,
        jsonb_agg(jsonb_build_object('id', p.id, 'name', (COALESCE(p.first_name, ''::character varying)::text || 
        ' '::text) || COALESCE(p.last_name, ''::character varying)::text)) AS observers
      FROM observer o1
         JOIN profile p ON o1.profile_id = p.id
         JOIN transectmethod tm ON o1.transectmethod_id = tm.id
         JOIN transectmethod_habitatcomplexity tt_1 ON tm.id = tt_1.transectmethod_ptr_id
      GROUP BY tt_1.transect_id
  ) observers ON su.id = observers.transect_id
  JOIN vw_sample_events se ON su.sample_event_id = se.sample_event_id;
    """.format(
        se_fields=", ".join([f"se.{f}" for f in BaseSUViewModel.se_fields]),
        su_fields=BaseSUViewModel.su_fields_sql,
    )

    reverse_sql = "DROP VIEW IF EXISTS public.vw_habitatcomplexity_obs CASCADE;"

    sample_unit_id = models.UUIDField()
    sample_time = models.TimeField()
    transect_number = models.PositiveSmallIntegerField()
    transect_len_surveyed = models.PositiveSmallIntegerField(
        verbose_name=_("transect length surveyed (m)")
    )
    reef_slope = models.CharField(max_length=50)
    interval_size = models.DecimalField(
        max_digits=4, decimal_places=2, default=0.5, verbose_name=_("interval size (m)")
    )
    interval = models.DecimalField(max_digits=7, decimal_places=2)
    observation_notes = models.TextField(blank=True)
    score = models.PositiveSmallIntegerField()
    score_name = models.CharField(max_length=100)
    data_policy_habitatcomplexity = models.CharField(max_length=50)

    class Meta:
        db_table = "vw_habitatcomplexity_obs"
        managed = False


class HabitatComplexitySUView(BaseSUViewModel):
    project_lookup = "project_id"

    # Unique combination of these fields defines a single (pseudo) sample unit. All other fields are aggregated.
    su_fields = BaseSUViewModel.se_fields + [
        "depth",
        "transect_number",
        "transect_len_surveyed",
        "interval_size",
        "data_policy_habitatcomplexity",
    ]

    sql = """
CREATE OR REPLACE VIEW vw_habitatcomplexity_su AS 
SELECT NULL AS id,
habcomp_su.pseudosu_id, 
{su_fields},
{agg_su_fields},
reef_slope, 
score_avg
FROM (
    SELECT su.pseudosu_id,
    json_agg(DISTINCT su.sample_unit_id) AS sample_unit_ids,
    {su_fields_qualified},
    {su_aggfields_sql},
    string_agg(DISTINCT reef_slope::text, ', '::text ORDER BY (reef_slope::text)) AS reef_slope,
    ROUND(AVG(score), 2) AS score_avg

    FROM vw_habitatcomplexity_obs
    INNER JOIN sample_unit_cache su ON (vw_habitatcomplexity_obs.sample_unit_id = su.sample_unit_id)
    GROUP BY su.pseudosu_id,
    {su_fields_qualified}
) habcomp_su

INNER JOIN (
    SELECT pseudosu_id,
    jsonb_agg(DISTINCT observer) AS observers

    FROM (
        SELECT su.pseudosu_id,
        jsonb_array_elements(observers) AS observer
        FROM vw_habitatcomplexity_obs
        INNER JOIN sample_unit_cache su ON (vw_habitatcomplexity_obs.sample_unit_id = su.sample_unit_id)
        GROUP BY su.pseudosu_id, 
        observers
    ) habcomp_obs_obs
    GROUP BY pseudosu_id
) habcomp_obs
ON (habcomp_su.pseudosu_id = habcomp_obs.pseudosu_id);
    """.format(
        su_fields=", ".join(su_fields),
        su_fields_qualified=", ".join(
            [f"vw_habitatcomplexity_obs.{f}" for f in su_fields]
        ),
        agg_su_fields=", ".join(BaseSUViewModel.agg_su_fields),
        su_aggfields_sql=BaseSUViewModel.su_aggfields_sql,
    )

    reverse_sql = "DROP VIEW IF EXISTS public.vw_habitatcomplexity_su CASCADE;"

    sample_unit_ids = JSONField()
    transect_number = models.PositiveSmallIntegerField()
    transect_len_surveyed = models.PositiveSmallIntegerField(
        verbose_name=_("transect length surveyed (m)")
    )
    reef_slope = models.CharField(max_length=50)
    score_avg = models.DecimalField(decimal_places=2, max_digits=3)
    data_policy_habitatcomplexity = models.CharField(max_length=50)

    objects = ExtendedManager()

    class Meta:
        db_table = "vw_habitatcomplexity_su"
        managed = False


class HabitatComplexitySEView(BaseViewModel):
    project_lookup = "project_id"

    sql = """
CREATE OR REPLACE VIEW vw_habitatcomplexity_se AS 
SELECT sample_event_id AS id,
{se_fields},
data_policy_habitatcomplexity,
{su_aggfields_sql},
COUNT(pseudosu_id) AS sample_unit_count,
ROUND(AVG(score_avg), 2) AS score_avg_avg
FROM vw_habitatcomplexity_su
GROUP BY 
{se_fields}, 
data_policy_habitatcomplexity
    """.format(
        se_fields=", ".join(
            [f"vw_habitatcomplexity_su.{f}" for f in BaseViewModel.se_fields]
        ),
        su_aggfields_sql=BaseViewModel.su_aggfields_sql,
    )

    reverse_sql = "DROP VIEW IF EXISTS public.vw_habitatcomplexity_se CASCADE;"

    sample_unit_count = models.PositiveSmallIntegerField()
    depth_avg = models.DecimalField(
        max_digits=4, decimal_places=2, verbose_name=_("depth (m)")
    )
    score_avg_avg = models.DecimalField(decimal_places=2, max_digits=3)
    data_policy_habitatcomplexity = models.CharField(max_length=50)

    objects = ExtendedManager()

    class Meta:
        db_table = "vw_habitatcomplexity_se"
        managed = False
