from time import sleep

from api.covariates import update_site_covariates
from api.models import Site
from .progress_bar_base_command import ProgressBarBaseCommand


class Command(ProgressBarBaseCommand):
    help = "Update site covariatess"

    def add_arguments(self, parser):
        parser.add_argument(
            "--throttle",
            type=int,
            default=50,
            help="Number of sites to fetch before sleeping 1 second.",
        )

        parser.add_argument(
            "--project_id",
            type=str,
            help="Only update sites related to this project id",
        )

    def handle(self, *args, **options):
        throttle = options["throttle"]
        project_id = options["project_id"]

        if project_id:
            qry = Site.objects.filter(project_id=project_id)
        else:
            qry = Site.objects.all()

        num_sites = qry.count()
        self.draw_progress_bar(0)
        for n, site in enumerate(qry):
            self.draw_progress_bar(float(n) / num_sites)
            update_site_covariates(site)
            if n % throttle == 0:
                sleep(1)

        self.draw_progress_bar(1)
