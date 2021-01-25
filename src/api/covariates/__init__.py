from api.decorators import run_in_thread
from api.models import Covariate, Site
from .coral_atlas import CoralAtlasCovariate


@run_in_thread
def update_site_covariates(site):
    site_pk = site.pk

    point = site.location
    existing_covariates = set(site.covariates.all().values_list("name", flat=True))
    supported_covariates = set(Covariate.SUPPORTED_COVARIATES)

    if (
        site_pk
        and Site.objects.get(pk=site_pk).location == point
        and not supported_covariates.difference(existing_covariates)
    ):
        return

    coral_atlas = CoralAtlasCovariate()
    results = coral_atlas.fetch([(point.x, point.y)])

    if not results:
        return

    result = results[0]

    data_date = result["date"]
    requested_date = result["requested_date"]
    aca_covariates = result.get("covariates") or dict()
    aca_benthic = aca_covariates["aca_benthic"]
    aca_geomorphic = aca_covariates["aca_geomorphic"]

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
