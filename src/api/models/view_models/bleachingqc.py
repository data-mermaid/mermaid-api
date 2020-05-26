from django.utils.translation import ugettext_lazy as _
from ..base import ExtendedManager
from .base import *


class BleachingQCColoniesBleachedObsView(BaseViewModel):
    sql = """
CREATE OR REPLACE VIEW vw_bleachingqc_colonies_bleached_obs AS
SELECT
  o.id,
  {se_fields},
  se.sample_event_id,
  se.current_name,
  se.tide_name,
  se.visibility_name,
  se.sample_time,
  se.sample_event_notes,
  se.data_policy_bleachingqc,
  observers.observers,
  tt.transectmethod_ptr_id AS sample_unit_id,
  qc.label,
  qc.quadrat_size,
  b.name AS benthic_attribute,
  gf.name AS growth_form,
  o.count_normal,
  o.count_pale,
  o.count_20,
  o.count_50,
  o.count_80,
  o.count_100,
  o.count_dead
FROM
  obs_colonies_bleached o
  JOIN benthic_attribute b ON o.attribute_id = b.id
  LEFT JOIN growth_form gf ON o.growth_form_id = gf.id
  JOIN transectmethod_bleaching_quadrat_collection tt ON o.bleachingquadratcollection_id = tt.transectmethod_ptr_id
  JOIN quadrat_collection qc ON tt.quadrat_id = qc.id
  JOIN (
    SELECT
      tt_1.quadrat_id,
      jsonb_agg(
        jsonb_build_object(
          'id',
          p.id,
          'name',
          (
            COALESCE(p.first_name, '' :: character varying) :: text || ' ' :: text
          ) || COALESCE(p.last_name, '' :: character varying) :: text
        )
      ) AS observers
    FROM
      observer o1
      JOIN profile p ON o1.profile_id = p.id
      JOIN transectmethod tm ON o1.transectmethod_id = tm.id
      JOIN transectmethod_bleaching_quadrat_collection tt_1 ON tm.id = tt_1.transectmethod_ptr_id
    GROUP BY
      tt_1.quadrat_id
  ) observers ON qc.id = observers.quadrat_id
  JOIN vw_sample_events se ON qc.sample_event_id = se.sample_event_id
    """.format(
        se_fields=", ".join([f"se.{f}" for f in BaseViewModel.se_fields])
    )

    sample_event_id = models.UUIDField()
    sample_event_notes = models.TextField(blank=True)
    sample_unit_id = models.UUIDField()
    sample_time = models.TimeField()
    observers = JSONField(null=True, blank=True)
    label = models.CharField(max_length=50, blank=True)
    quadrat_size = models.DecimalField(decimal_places=2, max_digits=6)
    depth = models.DecimalField(
        max_digits=3, decimal_places=1, verbose_name=_("depth (m)")
    )
    benthic_attribute = models.CharField(max_length=100)
    growth_form = models.CharField(max_length=100)
    count_normal = models.PositiveSmallIntegerField(verbose_name=u'normal', default=0)
    count_pale = models.PositiveSmallIntegerField(verbose_name=u'pale', default=0)
    count_20 = models.PositiveSmallIntegerField(verbose_name=u'0-20% bleached', default=0)
    count_50 = models.PositiveSmallIntegerField(verbose_name=u'20-50% bleached', default=0)
    count_80 = models.PositiveSmallIntegerField(verbose_name=u'50-80% bleached', default=0)
    count_100 = models.PositiveSmallIntegerField(verbose_name=u'80-100% bleached', default=0)
    count_dead = models.PositiveSmallIntegerField(verbose_name=u'recently dead', default=0)
    data_policy_bleachingqc = models.CharField(max_length=50)

    class Meta:
        db_table = "vw_bleachingqc_colonies_bleached_obs"
        managed = False


class BleachingQCQuadratBenthicPercentObsView(BaseViewModel):
    sql = """
    """.format(
        se_fields=", ".join([f"se.{f}" for f in BaseViewModel.se_fields])
    )

    class Meta:
        db_table = "vw_bleachingqc_quadrat_benthic_percent_obs"
        managed = False


class BleachingQCSUView(BaseViewModel):
    project_lookup = "project_id"
    sql = """
    """.format(
        se_fields=", ".join(BaseViewModel.se_fields)
    )

    objects = ExtendedManager()

    class Meta:
        db_table = "vw_bleachingqc_su"
        managed = False


class BleachingQCSEView(BaseViewModel):
    project_lookup = "project_id"
    sql = """
    """

    objects = ExtendedManager()

    class Meta:
        db_table = "vw_bleachingqc_se"
        managed = False
