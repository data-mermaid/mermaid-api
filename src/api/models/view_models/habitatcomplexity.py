from django.utils.translation import ugettext_lazy as _
from ..base import ExtendedManager
from .base import *


class HabitatComplexityObsView(BaseViewModel):
    sql = """
CREATE OR REPLACE VIEW vw_habitatcomplexity_obs AS 
SELECT
  o.id,
  {se_fields},
  se.sample_event_id,
  se.current_name,
  se.tide_name,
  se.visibility_name,
  se.sample_time,
  se.sample_event_notes,
  se.data_policy_habitatcomplexity,
  observers.observers,
  tt.transectmethod_ptr_id AS sample_unit_id,
  tb.number AS transect_number,
  tb.label,
  tb.len_surveyed AS transect_len_surveyed,
  rs.name AS reef_slope,
  o."interval",
  s.val AS score,
  o.notes AS observation_notes
FROM
  obs_habitatcomplexity o
  INNER JOIN api_habitatcomplexityscore s ON (o.score_id = s.id)
  INNER JOIN transectmethod_habitatcomplexity tt ON o.habitatcomplexity_id = tt.transectmethod_ptr_id
  INNER JOIN transect_benthic tb ON tt.transect_id = tb.id
  LEFT JOIN api_reefslope rs ON tb.reef_slope_id = rs.id
  JOIN ( 
      SELECT tt_1.transect_id,
        jsonb_agg(jsonb_build_object('id', p.id, 'name', (COALESCE(p.first_name, ''::character varying)::text || 
        ' '::text) || COALESCE(p.last_name, ''::character varying)::text)) AS observers
      FROM observer o1
         JOIN profile p ON o1.profile_id = p.id
         JOIN transectmethod tm ON o1.transectmethod_id = tm.id
         JOIN transectmethod_habitatcomplexity tt_1 ON tm.id = tt_1.transectmethod_ptr_id
      GROUP BY tt_1.transect_id
  ) observers ON tb.id = observers.transect_id
  JOIN vw_sample_events se ON tb.sample_event_id = se.sample_event_id
    """.format(
        se_fields=", ".join([f"se.{f}" for f in BaseViewModel.se_fields])
    )

    reverse_sql = "DROP VIEW IF EXISTS public.vw_habitatcomplexity_obs CASCADE;"

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
    interval = models.DecimalField(max_digits=7, decimal_places=2)
    observation_notes = models.TextField(blank=True)
    score = models.PositiveSmallIntegerField()
    data_policy_habitatcomplexity = models.CharField(max_length=50)

    class Meta:
        db_table = "vw_habitatcomplexity_obs"
        managed = False


class HabitatComplexitySUView(BaseViewModel):
    project_lookup = "project_id"

    sql = """
CREATE OR REPLACE VIEW vw_habitatcomplexity_su AS 
SELECT
  sample_unit_id AS id,
  label, current_name, tide_name, visibility_name, data_policy_habitatcomplexity, observers,
  {se_fields},
  transect_number,
  transect_len_surveyed,
  reef_slope,
  ROUND(AVG(score), 2) AS score_avg
FROM
  vw_habitatcomplexity_obs
GROUP BY
  sample_unit_id,
  label, current_name, tide_name, visibility_name, data_policy_habitatcomplexity, observers,
  {se_fields},
  transect_number,
  transect_len_surveyed,
  reef_slope
    """.format(
        se_fields=", ".join(BaseViewModel.se_fields)
    )

    reverse_sql = "DROP VIEW IF EXISTS public.vw_habitatcomplexity_su CASCADE;"

    observers = JSONField(null=True, blank=True)
    transect_number = models.PositiveSmallIntegerField()
    transect_len_surveyed = models.PositiveSmallIntegerField(
        verbose_name=_("transect length surveyed (m)")
    )
    depth = models.DecimalField(
        max_digits=3, decimal_places=1, verbose_name=_("depth (m)")
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
    # TODO: refactor once SE/SU refactoring is done
    sefields_minus_depth = [
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
        "data_policy_habitatcomplexity",
    ]

    sql = """
CREATE OR REPLACE VIEW vw_habitatcomplexity_se AS 
SELECT
  NULL AS id,
  {se_fields},
  COUNT(id) AS sample_unit_count,
  ROUND(AVG("depth"), 2) as depth_avg,
  string_agg(DISTINCT current_name, ', ' ORDER BY current_name) AS current_name,
  string_agg(DISTINCT tide_name, ', ' ORDER BY tide_name) AS tide_name,
  string_agg(DISTINCT visibility_name, ', ' ORDER BY visibility_name) AS visibility_name,
  ROUND(AVG(score_avg), 2) AS score_avg_avg,
  data_policy_habitatcomplexity
FROM vw_habitatcomplexity_su
GROUP BY {se_fields}, data_policy_habitatcomplexity
      """.format(
        se_fields=", ".join(BaseViewModel.se_fields)
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
