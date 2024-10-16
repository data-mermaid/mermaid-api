import uuid

from django.contrib.gis.db import models
from django.utils.translation import gettext_lazy as _

from .mermaid import Project


class BaseSummaryModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project_id = models.UUIDField(db_index=True)
    project_name = models.CharField(max_length=255)
    project_status = models.PositiveSmallIntegerField(
        choices=Project.STATUSES, default=Project.OPEN
    )
    project_notes = models.TextField(blank=True)
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
    reef_type = models.CharField(max_length=50, null=True, blank=True)
    reef_zone = models.CharField(max_length=50, null=True, blank=True)
    reef_exposure = models.CharField(max_length=50, null=True, blank=True)
    management_id = models.UUIDField()
    management_name = models.CharField(max_length=255)
    management_name_secondary = models.CharField(max_length=255, null=True, blank=True)
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

    created_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


class BaseObsModel(BaseSummaryModel):
    label = models.CharField(max_length=50, blank=True)
    relative_depth = models.CharField(max_length=50, null=True, blank=True)
    sample_time = models.TimeField(null=True, blank=True)
    observers = models.JSONField(null=True, blank=True)
    current_name = models.CharField(max_length=50, null=True, blank=True)
    tide_name = models.CharField(max_length=50, null=True, blank=True)
    visibility_name = models.CharField(max_length=50, null=True, blank=True)
    sample_unit_notes = models.TextField(blank=True)
    # Fields common to all SUs that are actually SU properties (that make SUs distinct)
    depth = models.DecimalField(max_digits=3, decimal_places=1, verbose_name=_("depth (m)"))

    class Meta:
        abstract = True


class BaseSUModel(BaseSummaryModel):
    label = models.TextField(blank=True)
    relative_depth = models.TextField(null=True, blank=True)
    sample_time = models.TextField(null=True, blank=True)
    observers = models.JSONField(null=True, blank=True)
    current_name = models.TextField(null=True, blank=True)
    tide_name = models.TextField(null=True, blank=True)
    visibility_name = models.TextField(null=True, blank=True)
    sample_unit_notes = models.TextField(blank=True)
    # Fields common to all SUs that are actually SU properties (that make SUs distinct)
    depth = models.DecimalField(max_digits=3, decimal_places=1, verbose_name=_("depth (m)"))

    class Meta:
        abstract = True


class BeltFishObsModel(BaseObsModel):
    sample_unit_id = models.UUIDField()
    transect_number = models.PositiveSmallIntegerField()
    transect_len_surveyed = models.PositiveSmallIntegerField(
        verbose_name=_("transect length surveyed (m)")
    )
    transect_width_name = models.CharField(max_length=100, null=True, blank=True)
    assigned_transect_width_m = models.PositiveSmallIntegerField(null=True, blank=True)
    reef_slope = models.CharField(max_length=50, null=True, blank=True)
    fish_family = models.CharField(max_length=100, null=True, blank=True)
    fish_genus = models.CharField(max_length=100, null=True, blank=True)
    fish_taxon = models.CharField(max_length=100, null=True, blank=True)
    trophic_group = models.CharField(max_length=100, null=True, blank=True)
    trophic_level = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    functional_group = models.CharField(max_length=100, null=True, blank=True)
    vulnerability = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    biomass_constant_a = models.DecimalField(max_digits=7, decimal_places=6, null=True, blank=True)
    biomass_constant_b = models.DecimalField(max_digits=7, decimal_places=6, null=True, blank=True)
    biomass_constant_c = models.DecimalField(
        max_digits=7, decimal_places=6, default=1, null=True, blank=True
    )
    size_bin = models.CharField(max_length=100)
    size = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        verbose_name=_("size (cm)"),
        null=True,
        blank=True,
    )
    count = models.PositiveIntegerField(default=1, null=True, blank=True)
    biomass_kgha = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        verbose_name=_("biomass (kg/ha)"),
        null=True,
        blank=True,
    )
    observation_notes = models.TextField(null=True, blank=True)
    data_policy_beltfish = models.CharField(max_length=50)
    pseudosu_id = models.UUIDField()

    class Meta:
        db_table = "summary_belt_fish_obs"


class BeltFishSUModel(BaseSUModel):
    sample_unit_ids = models.JSONField()
    total_abundance = models.PositiveIntegerField()
    transect_number = models.PositiveSmallIntegerField()
    transect_len_surveyed = models.PositiveSmallIntegerField(
        verbose_name=_("transect length surveyed (m)")
    )
    transect_width_name = models.CharField(max_length=100, null=True, blank=True)
    reef_slope = models.CharField(max_length=50, null=True, blank=True)
    size_bin = models.CharField(max_length=100)
    biomass_kgha = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name=_("biomass (kg/ha)"),
        null=True,
        blank=True,
    )
    biomass_kgha_trophic_group = models.JSONField(null=True, blank=True)
    biomass_kgha_fish_family = models.JSONField(null=True, blank=True)
    data_policy_beltfish = models.CharField(max_length=50)
    pseudosu_id = models.UUIDField()
    biomass_kgha_trophic_group_zeroes = models.JSONField(null=True, blank=True)
    biomass_kgha_fish_family_zeroes = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "summary_belt_fish_su"


class BeltFishSEModel(BaseSummaryModel):
    sample_unit_count = models.PositiveSmallIntegerField()
    depth_avg = models.DecimalField(
        max_digits=4, decimal_places=2, verbose_name=_("depth mean (m)")
    )
    depth_sd = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        verbose_name=_("depth standard deviation (m)"),
        blank=True,
        null=True,
    )
    current_name = models.CharField(max_length=100, null=True, blank=True)
    tide_name = models.CharField(max_length=100, null=True, blank=True)
    visibility_name = models.CharField(max_length=100, null=True, blank=True)
    biomass_kgha_avg = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name=_("biomass mean (kg/ha)"),
        null=True,
        blank=True,
    )
    biomass_kgha_sd = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name=_("biomass standard deviation (kg/ha)"),
        blank=True,
        null=True,
    )
    biomass_kgha_trophic_group_avg = models.JSONField(null=True, blank=True)
    biomass_kgha_trophic_group_sd = models.JSONField(null=True, blank=True)
    biomass_kgha_fish_family_avg = models.JSONField(null=True, blank=True)
    biomass_kgha_fish_family_sd = models.JSONField(null=True, blank=True)
    data_policy_beltfish = models.CharField(max_length=50)

    class Meta:
        db_table = "summary_belt_fish_se"


class BenthicPITObsModel(BaseObsModel):
    sample_unit_id = models.UUIDField()
    transect_number = models.PositiveSmallIntegerField()
    transect_len_surveyed = models.PositiveSmallIntegerField(
        verbose_name=_("transect length surveyed (m)")
    )
    reef_slope = models.CharField(max_length=50, null=True, blank=True)
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
    benthic_category = models.CharField(max_length=100, null=True, blank=True)
    benthic_attribute = models.CharField(max_length=100, null=True, blank=True)
    growth_form = models.CharField(max_length=100, null=True, blank=True)
    life_histories = models.JSONField(null=True, blank=True)
    observation_notes = models.TextField(blank=True)
    data_policy_benthicpit = models.CharField(max_length=50)
    pseudosu_id = models.UUIDField()

    class Meta:
        db_table = "summary_benthicpit_obs"


class BenthicPITSUModel(BaseSUModel):
    sample_unit_ids = models.JSONField()
    transect_number = models.PositiveSmallIntegerField()
    transect_len_surveyed = models.PositiveSmallIntegerField(
        verbose_name=_("transect length surveyed (m)")
    )
    reef_slope = models.CharField(max_length=50, null=True, blank=True)
    interval_size = models.DecimalField(
        max_digits=4, decimal_places=2, default=0.5, verbose_name=_("interval size (m)")
    )
    interval_start = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0.5,
        verbose_name=_("interval start (m)"),
    )
    percent_cover_benthic_category = models.JSONField(null=True, blank=True)
    percent_cover_life_histories = models.JSONField(null=True, blank=True)
    data_policy_benthicpit = models.CharField(max_length=50)
    pseudosu_id = models.UUIDField()

    class Meta:
        db_table = "summary_benthicpit_su"


class BenthicPITSEModel(BaseSummaryModel):
    sample_unit_count = models.PositiveSmallIntegerField()
    depth_avg = models.DecimalField(
        max_digits=4, decimal_places=2, verbose_name=_("depth mean (m)")
    )
    depth_sd = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        verbose_name=_("depth standard deviation (m)"),
        blank=True,
        null=True,
    )
    current_name = models.CharField(max_length=100, null=True, blank=True)
    tide_name = models.CharField(max_length=100, null=True, blank=True)
    visibility_name = models.CharField(max_length=100, null=True, blank=True)
    percent_cover_benthic_category_avg = models.JSONField(null=True, blank=True)
    percent_cover_benthic_category_sd = models.JSONField(null=True, blank=True)
    percent_cover_life_histories_avg = models.JSONField(null=True, blank=True)
    percent_cover_life_histories_sd = models.JSONField(null=True, blank=True)
    data_policy_benthicpit = models.CharField(max_length=50)

    class Meta:
        db_table = "summary_benthicpit_se"


class BenthicLITObsModel(BaseObsModel):
    sample_unit_id = models.UUIDField()
    transect_number = models.PositiveSmallIntegerField()
    relative_depth = models.CharField(max_length=50, null=True, blank=True)
    transect_len_surveyed = models.PositiveSmallIntegerField(
        verbose_name=_("transect length surveyed (m)")
    )
    reef_slope = models.CharField(max_length=50, null=True, blank=True)
    length = models.PositiveSmallIntegerField()
    total_length = models.PositiveIntegerField()
    benthic_category = models.CharField(max_length=100, null=True, blank=True)
    benthic_attribute = models.CharField(max_length=100, null=True, blank=True)
    growth_form = models.CharField(max_length=100, null=True, blank=True)
    life_histories = models.JSONField(null=True, blank=True)
    observation_notes = models.TextField(blank=True)
    data_policy_benthiclit = models.CharField(max_length=50)
    pseudosu_id = models.UUIDField()

    class Meta:
        db_table = "summary_benthiclit_obs"


class BenthicLITSUModel(BaseSUModel):
    sample_unit_ids = models.JSONField()
    transect_number = models.PositiveSmallIntegerField()
    transect_len_surveyed = models.PositiveSmallIntegerField(
        verbose_name=_("transect length surveyed (m)")
    )
    total_length = models.PositiveIntegerField()
    reef_slope = models.CharField(max_length=50, null=True, blank=True)
    percent_cover_benthic_category = models.JSONField(null=True, blank=True)
    percent_cover_life_histories = models.JSONField(null=True, blank=True)
    data_policy_benthiclit = models.CharField(max_length=50)
    pseudosu_id = models.UUIDField()

    class Meta:
        db_table = "summary_benthiclit_su"


class BenthicLITSEModel(BaseSummaryModel):
    sample_unit_count = models.PositiveSmallIntegerField()
    depth_avg = models.DecimalField(
        max_digits=4, decimal_places=2, verbose_name=_("depth mean (m)")
    )
    depth_sd = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        verbose_name=_("depth standard deviation (m)"),
        blank=True,
        null=True,
    )
    current_name = models.CharField(max_length=100, null=True, blank=True)
    tide_name = models.CharField(max_length=100, null=True, blank=True)
    visibility_name = models.CharField(max_length=100, null=True, blank=True)
    percent_cover_benthic_category_avg = models.JSONField(null=True, blank=True)
    percent_cover_benthic_category_sd = models.JSONField(null=True, blank=True)
    percent_cover_life_histories_avg = models.JSONField(null=True, blank=True)
    percent_cover_life_histories_sd = models.JSONField(null=True, blank=True)
    data_policy_benthiclit = models.CharField(max_length=50)

    class Meta:
        db_table = "summary_benthiclit_se"


class BenthicPhotoQuadratTransectObsModel(BaseObsModel):
    sample_unit_id = models.UUIDField()
    transect_number = models.PositiveSmallIntegerField()
    relative_depth = models.CharField(max_length=50, null=True, blank=True)
    transect_len_surveyed = models.PositiveSmallIntegerField(
        verbose_name=_("transect length surveyed (m)")
    )
    quadrat_size = models.DecimalField(decimal_places=2, max_digits=6)
    num_quadrats = models.PositiveSmallIntegerField()
    num_points_per_quadrat = models.PositiveSmallIntegerField()
    reef_slope = models.CharField(max_length=50, null=True, blank=True)
    quadrat_number = models.PositiveSmallIntegerField(verbose_name="quadrat number")
    benthic_category = models.CharField(max_length=100, null=True, blank=True)
    benthic_attribute = models.CharField(max_length=100, null=True, blank=True)
    growth_form = models.CharField(max_length=100, null=True, blank=True)
    num_points = models.PositiveSmallIntegerField()
    observation_notes = models.TextField(blank=True)
    data_policy_benthicpqt = models.CharField(max_length=50)
    pseudosu_id = models.UUIDField()

    class Meta:
        db_table = "summary_benthicpqt_obs"


class BenthicPhotoQuadratTransectSUModel(BaseSUModel):
    sample_unit_ids = models.JSONField()
    transect_number = models.PositiveSmallIntegerField()
    transect_len_surveyed = models.PositiveSmallIntegerField(
        verbose_name=_("transect length surveyed (m)")
    )
    num_points_nonother = models.PositiveSmallIntegerField(
        verbose_name="number of non-'Other' points for all observations in all quadrats for the transect"
    )
    reef_slope = models.CharField(max_length=50, null=True, blank=True)
    percent_cover_benthic_category = models.JSONField(null=True, blank=True)
    data_policy_benthicpqt = models.CharField(max_length=50)
    pseudosu_id = models.UUIDField()

    class Meta:
        db_table = "summary_benthicpqt_su"


class BenthicPhotoQuadratTransectSEModel(BaseSummaryModel):
    sample_unit_count = models.PositiveSmallIntegerField()
    depth_avg = models.DecimalField(
        max_digits=4, decimal_places=2, verbose_name=_("depth mean (m)")
    )
    depth_sd = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        verbose_name=_("depth standard deviation (m)"),
        blank=True,
        null=True,
    )
    current_name = models.CharField(max_length=100, null=True, blank=True)
    tide_name = models.CharField(max_length=100, null=True, blank=True)
    visibility_name = models.CharField(max_length=100, null=True, blank=True)
    num_points_nonother = models.PositiveSmallIntegerField(
        verbose_name="number of non-'Other' points for all observations in all transects for the sample event"
    )
    percent_cover_benthic_category_avg = models.JSONField(null=True, blank=True)
    percent_cover_benthic_category_sd = models.JSONField(null=True, blank=True)
    data_policy_benthicpqt = models.CharField(max_length=50)

    class Meta:
        db_table = "summary_benthicpqt_se"


class BleachingQCColoniesBleachedObsModel(BaseObsModel):
    sample_unit_id = models.UUIDField()
    quadrat_size = models.DecimalField(decimal_places=2, max_digits=6)
    benthic_attribute = models.CharField(max_length=100, null=True, blank=True)
    growth_form = models.CharField(max_length=100, null=True, blank=True)
    count_normal = models.PositiveSmallIntegerField(verbose_name="normal", default=0)
    count_pale = models.PositiveSmallIntegerField(verbose_name="pale", default=0)
    count_20 = models.PositiveSmallIntegerField(verbose_name="0-20% bleached", default=0)
    count_50 = models.PositiveSmallIntegerField(verbose_name="20-50% bleached", default=0)
    count_80 = models.PositiveSmallIntegerField(verbose_name="50-80% bleached", default=0)
    count_100 = models.PositiveSmallIntegerField(verbose_name="80-100% bleached", default=0)
    count_dead = models.PositiveSmallIntegerField(verbose_name="recently dead", default=0)
    observation_notes = models.TextField(blank=True)
    data_policy_bleachingqc = models.CharField(max_length=50)

    class Meta:
        db_table = "summary_bleachingqc_colonies_bleached_obs"


class BleachingQCQuadratBenthicPercentObsModel(BaseObsModel):
    sample_unit_id = models.UUIDField()
    quadrat_size = models.DecimalField(decimal_places=2, max_digits=6)
    quadrat_number = models.PositiveSmallIntegerField(verbose_name="quadrat number")
    percent_hard = models.PositiveSmallIntegerField(
        verbose_name="hard coral, % cover", default=0, null=True, blank=True
    )
    percent_soft = models.PositiveSmallIntegerField(
        verbose_name="soft coral, % cover", default=0, null=True, blank=True
    )
    percent_algae = models.PositiveSmallIntegerField(
        verbose_name="macroalgae, % cover", default=0, null=True, blank=True
    )
    observation_notes = models.TextField(blank=True)
    data_policy_bleachingqc = models.CharField(max_length=50)

    class Meta:
        db_table = "summary_bleachingqc_quadrat_benthic_percent_obs"


class BleachingQCSUModel(BaseSUModel):
    sample_unit_ids = models.JSONField()
    quadrat_size = models.DecimalField(decimal_places=2, max_digits=6)
    count_genera = models.PositiveSmallIntegerField(default=0)
    count_total = models.PositiveSmallIntegerField(default=0)
    percent_normal = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    percent_pale = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    percent_20 = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    percent_50 = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    percent_80 = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    percent_100 = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    percent_dead = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    percent_bleached = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    quadrat_count = models.PositiveSmallIntegerField(default=0, null=True, blank=True)
    percent_hard_avg = models.DecimalField(
        max_digits=4, decimal_places=1, default=0, null=True, blank=True
    )
    percent_hard_sd = models.DecimalField(
        max_digits=4, decimal_places=1, default=0, null=True, blank=True
    )
    percent_soft_avg = models.DecimalField(
        max_digits=4, decimal_places=1, default=0, null=True, blank=True
    )
    percent_soft_sd = models.DecimalField(
        max_digits=4, decimal_places=1, default=0, null=True, blank=True
    )
    percent_algae_avg = models.DecimalField(
        max_digits=4, decimal_places=1, default=0, null=True, blank=True
    )
    percent_algae_sd = models.DecimalField(
        max_digits=4, decimal_places=1, default=0, null=True, blank=True
    )
    data_policy_bleachingqc = models.CharField(max_length=50)
    pseudosu_id = models.UUIDField()

    class Meta:
        db_table = "summary_bleachingqc_su"


class BleachingQCSEModel(BaseSummaryModel):
    sample_unit_count = models.PositiveSmallIntegerField()
    depth_avg = models.DecimalField(
        max_digits=4, decimal_places=2, verbose_name=_("depth mean (m)")
    )
    depth_sd = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        verbose_name=_("depth standard deviation (m)"),
        blank=True,
        null=True,
    )
    current_name = models.CharField(max_length=100, null=True, blank=True)
    tide_name = models.CharField(max_length=100, null=True, blank=True)
    visibility_name = models.CharField(max_length=100, null=True, blank=True)
    quadrat_size_avg = models.DecimalField(decimal_places=2, max_digits=6)
    count_total_avg = models.DecimalField(max_digits=5, decimal_places=1)
    count_total_sd = models.DecimalField(max_digits=5, decimal_places=1, blank=True, null=True)
    count_genera_avg = models.DecimalField(max_digits=4, decimal_places=1)
    count_genera_sd = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
    percent_normal_avg = models.DecimalField(max_digits=4, decimal_places=1)
    percent_normal_sd = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
    percent_pale_avg = models.DecimalField(max_digits=4, decimal_places=1)
    percent_pale_sd = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
    percent_20_avg = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    percent_20_sd = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
    percent_50_avg = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    percent_50_sd = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
    percent_80_avg = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    percent_80_sd = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
    percent_100_avg = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    percent_100_sd = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
    percent_dead_avg = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    percent_dead_sd = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
    percent_bleached_avg = models.DecimalField(max_digits=4, decimal_places=1)
    percent_bleached_sd = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
    quadrat_count_avg = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    percent_hard_avg_avg = models.DecimalField(
        max_digits=4, decimal_places=1, null=True, blank=True
    )
    percent_hard_avg_sd = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    percent_soft_avg_avg = models.DecimalField(
        max_digits=4, decimal_places=1, null=True, blank=True
    )
    percent_soft_avg_sd = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    percent_algae_avg_avg = models.DecimalField(
        max_digits=4, decimal_places=1, null=True, blank=True
    )
    percent_algae_avg_sd = models.DecimalField(
        max_digits=4, decimal_places=1, null=True, blank=True
    )
    data_policy_bleachingqc = models.CharField(max_length=50)

    class Meta:
        db_table = "summary_bleachingqc_se"


class HabitatComplexityObsModel(BaseObsModel):
    sample_unit_id = models.UUIDField()
    sample_time = models.TimeField(null=True, blank=True)
    transect_number = models.PositiveSmallIntegerField()
    transect_len_surveyed = models.PositiveSmallIntegerField(
        verbose_name=_("transect length surveyed (m)")
    )
    reef_slope = models.CharField(max_length=50, null=True, blank=True)
    interval_size = models.DecimalField(
        max_digits=4, decimal_places=2, default=0.5, verbose_name=_("interval size (m)")
    )
    interval = models.DecimalField(max_digits=7, decimal_places=2)
    observation_notes = models.TextField(blank=True)
    score = models.PositiveSmallIntegerField()
    score_name = models.CharField(max_length=100, null=True, blank=True)
    data_policy_habitatcomplexity = models.CharField(max_length=50)
    pseudosu_id = models.UUIDField()

    class Meta:
        db_table = "summary_habitatcomplexity_obs"


class HabitatComplexitySUModel(BaseSUModel):
    sample_unit_ids = models.JSONField()
    transect_number = models.PositiveSmallIntegerField()
    transect_len_surveyed = models.PositiveSmallIntegerField(
        verbose_name=_("transect length surveyed (m)")
    )
    reef_slope = models.CharField(max_length=50, null=True, blank=True)
    score_avg = models.DecimalField(decimal_places=2, max_digits=3)
    score_sd = models.DecimalField(decimal_places=2, max_digits=3, null=True, blank=True)
    observation_count = models.PositiveSmallIntegerField()
    data_policy_habitatcomplexity = models.CharField(max_length=50)
    pseudosu_id = models.UUIDField()

    class Meta:
        db_table = "summary_habitatcomplexity_su"


class HabitatComplexitySEModel(BaseSummaryModel):
    sample_unit_count = models.PositiveSmallIntegerField()
    depth_avg = models.DecimalField(
        max_digits=4, decimal_places=2, verbose_name=_("depth mean (m)")
    )
    depth_sd = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        verbose_name=_("depth standard deviation (m)"),
        blank=True,
        null=True,
    )
    current_name = models.CharField(max_length=100, null=True, blank=True)
    tide_name = models.CharField(max_length=100, null=True, blank=True)
    visibility_name = models.CharField(max_length=100, null=True, blank=True)
    score_avg_avg = models.DecimalField(decimal_places=2, max_digits=3)
    score_avg_sd = models.DecimalField(decimal_places=2, max_digits=3, blank=True, null=True)
    observation_count_avg = models.DecimalField(decimal_places=2, max_digits=6)
    observation_count_sd = models.DecimalField(
        decimal_places=2, max_digits=6, blank=True, null=True
    )
    data_policy_habitatcomplexity = models.CharField(max_length=50)

    class Meta:
        db_table = "summary_habitatcomplexity_se"
