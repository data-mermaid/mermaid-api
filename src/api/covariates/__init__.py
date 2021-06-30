from api.decorators import run_in_thread
from api.models import Covariate, Site
from geopy.distance import distance as geopy_distance
from .coral_atlas import CoralAtlasCovariate


def update_site_covariates(site):
    site_pk = site.pk

    point = site.location
    north_pole = (90, 0)
    south_pole = (-90, 0)
    existing_covariates = set(site.covariates.all().values_list("name", flat=True))
    supported_covariates = set([c for c, _ in Covariate.SUPPORTED_COVARIATES])
    coral_atlas = CoralAtlasCovariate()

    existing_site = Site.objects.get_or_none(pk=site_pk)

    if (
        (
            site_pk and existing_site
            and existing_site.location == point
            and not supported_covariates.difference(existing_covariates)
        )
        or geopy_distance((point.y, point.x), north_pole).km < coral_atlas.radius
        or geopy_distance((point.y, point.x), south_pole).km < coral_atlas.radius
    ):
        return

    results = coral_atlas.fetch([(point.x, point.y)])

    if not results:
        return

    result = results[0]

    data_date = result["date"]
    requested_date = result["requested_date"]
    aca_covariates = result.get("covariates") or dict()
    aca_benthic = aca_covariates.get("aca_benthic") or []
    aca_geomorphic = aca_covariates.get("aca_geomorphic") or []

    aca_benthic_covariate = Covariate.objects.get_or_none(
        name="aca_benthic", site_id=site_pk
    ) or Covariate(name="aca_benthic", site=site)
    aca_benthic_covariate.display = "Alan Coral Atlas Benthic"
    aca_benthic_covariate.datestamp = data_date
    aca_benthic_covariate.requested_datestamp = requested_date
    aca_benthic_covariate.value = aca_benthic
    aca_benthic_covariate.save()

    aca_geomorphic_covariate = Covariate.objects.get_or_none(
        name="aca_geomorphic", site=site
    ) or Covariate(name="aca_geomorphic", site=site)
    aca_geomorphic_covariate.display = "Alan Coral Atlas Geomorphic"
    aca_geomorphic_covariate.datestamp = data_date
    aca_geomorphic_covariate.requested_datestamp = requested_date
    aca_geomorphic_covariate.value = aca_geomorphic
    aca_geomorphic_covariate.save()


@run_in_thread
def update_site_covariates_in_thread(site):
    update_site_covariates(site)
