import csv
from api.models.mermaid import Site


def run():
    with open("/var/projects/webapp/sites_sans_aca.csv", "w") as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(["project_id", "project_name", "site_name", "site_id", "lat", "lon"])

        sites = Site.objects.filter(project__status__gt=80)
        for site in sites:
            no_aca = False
            aca_covars = site.covariates.filter(name__startswith="aca_")
            for covar in aca_covars:
                if covar.value is None:
                    no_aca = True
            if no_aca:
                csvwriter.writerow(
                    [
                        site.project_id,
                        site.project.name,
                        site.name,
                        site.id,
                        site.location.y,
                        site.location.x,
                    ]
                )
                continue
