from api.decorators import run_in_thread
from api.models import Covariate, Site
from .coral_atlas import CoralAtlasCovariate
from .vibrant_oceans import VibrantOceansThreatsCovariate


def location_checks(site, covariate_cls, force=False):
    # ACA limits, but applicable generally
    lat_min = -85
    lat_max = 85
    lon_min = -180
    lon_max = 180

    point = site.location
    existing_site = Site.objects.get_or_none(pk=site.pk)

    return (
        (force is not False or (not existing_site or existing_site.location != point))
        and lat_min < point.y < lat_max
        and lon_min < point.x < lon_max
    )


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

    covariates = result.get("covariates") or dict()
    for key, cov in covariates.items():
        covariate = Covariate.objects.get_or_none(
            name=key, site_id=site_pk
        ) or Covariate(name=key, site_id=site_pk)
        covariate.display = vibrant_oceans_threats.display_name_lookup[key]
        covariate.datestamp = data_date
        covariate.requested_datestamp = requested_date
        covariate.value = cov
        covariate.save()


@run_in_thread
def update_site_covariates_in_thread(site, force=False):
    update_site_aca_covariates(site, force=force)
    update_site_vot_covariates(site, force=force)
