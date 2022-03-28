from django.conf import settings

from ..decorators import run_in_thread
from ..models import Covariate
from .coral_atlas import CoralAtlasCovariate
from .vibrant_oceans import VibrantOceansThreatsCovariate


def location_checks(site, covariate_cls, force=False):
    # ACA limits, but applicable generally
    lat_min = -85
    lat_max = 85
    lon_min = -180
    lon_max = 180

    point = site.location

    return lat_min < point.y < lat_max and lon_min < point.x < lon_max


def update_site_aca_covariates(site, force):
    coral_atlas = CoralAtlasCovariate()
    if location_checks(site, coral_atlas, force) is False:
        return

    site_pk = site.pk
    point = site.location

    results = coral_atlas.fetch([(point.x, point.y)])

    if not results:
        return

    result = results[0]

    data_date = result.get("date")
    requested_date = result.get("requested_date")

    if requested_date is None or data_date is None:
        return

    aca_covariates = result.get("covariates") or dict()
    aca_benthic = aca_covariates.get("aca_benthic")
    aca_geomorphic = aca_covariates.get("aca_geomorphic")

    aca_benthic_covariate = Covariate.objects.get_or_none(
        name="aca_benthic", site_id=site_pk
    ) or Covariate(name="aca_benthic", site_id=site_pk)
    aca_benthic_covariate.display = "Alan Coral Atlas Benthic"
    aca_benthic_covariate.datestamp = data_date
    aca_benthic_covariate.requested_datestamp = requested_date
    aca_benthic_covariate.value = aca_benthic
    aca_benthic_covariate.save()

    aca_geomorphic_covariate = Covariate.objects.get_or_none(
        name="aca_geomorphic", site_id=site_pk
    ) or Covariate(name="aca_geomorphic", site_id=site_pk)
    aca_geomorphic_covariate.display = "Alan Coral Atlas Geomorphic"
    aca_geomorphic_covariate.datestamp = data_date
    aca_geomorphic_covariate.requested_datestamp = requested_date
    aca_geomorphic_covariate.value = aca_geomorphic
    aca_geomorphic_covariate.save()


def update_site_vot_covariates(site, force):
    vibrant_oceans_threats = VibrantOceansThreatsCovariate()
    if location_checks(site, vibrant_oceans_threats, force) is False:
        return

    site_pk = site.pk
    point = site.location

    results = vibrant_oceans_threats.fetch([(point.x, point.y)])
    if not results or not results[0]:
        return

    result = results[0]

    data_date = result.get("date")
    requested_date = result.get("requested_date")

    if requested_date is None or data_date is None:
        return

    key_mapping = {
        vibrant_oceans_threats.SCORE: "beyer_score",
        vibrant_oceans_threats.SCORE_CN: "beyer_scorecn",
        vibrant_oceans_threats.SCORE_CY: "beyer_scorecy",
        vibrant_oceans_threats.SCORE_PFC: "beyer_scorepfc",
        vibrant_oceans_threats.SCORE_TH: "beyer_scoreth",
        vibrant_oceans_threats.SCORE_TR: "beyer_scoretr",
        vibrant_oceans_threats.GRAV_NC: "andrello_grav_nc",
        vibrant_oceans_threats.SEDIMENT: "andrello_sediment",
        vibrant_oceans_threats.NUTRIENT: "andrello_nutrient",
        vibrant_oceans_threats.POP_COUNT: "andrello_pop_count",
        vibrant_oceans_threats.NUM_PORTS: "andrello_num_ports",
        vibrant_oceans_threats.REEF_VALUE: "andrello_reef_value",
        vibrant_oceans_threats.CUMUL_SCORE: "andrello_cumul_score",
    }

    covariates = result.get("covariates") or dict()
    for key, cov in covariates.items():
        mapped_key = key_mapping.get(key)
        if mapped_key is None:
            continue

        covariate = Covariate.objects.get_or_none(
            name=mapped_key, site_id=site_pk
        ) or Covariate(name=mapped_key, site_id=site_pk)
        covariate.datestamp = data_date
        covariate.requested_datestamp = requested_date
        covariate.value = cov
        covariate.save()


def update_site_covariates(site, force=False):
    if settings.ENVIRONMENT in ("dev", "prod"):
        update_site_aca_covariates(site, force=force)
        update_site_vot_covariates(site, force=force)


@run_in_thread
def update_site_covariates_threaded(site, force=False):
    update_site_covariates(site, force=force)
