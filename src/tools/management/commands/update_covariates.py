import sys
from time import sleep

from django.core.management.base import BaseCommand

from api.covariates import update_site_covariates
from api.models import Site


class Command(BaseCommand):
    help = "Update site covariatess"

    def add_arguments(self, parser):
        parser.add_argument(
            "--throttle",
            type=int,
            default=50,
            help="Number of sites to fetch before sleeping 1 second.",
        )

    def draw_progress_bar(self, percent, bar_len=20):
        # percent float from 0 to 1.s
        sys.stdout.write("\r")
        symbols = "=" * int(bar_len * percent)
        sys.stdout.write(f"[{symbols:<{bar_len}}] {percent * 100:.0f}%")
        sys.stdout.flush()

        if percent == 1:
            print("")

    def handle(self, *args, **options):
        throttle = options["throttle"]

        num_sites = Site.objects.all().count()
        self.draw_progress_bar(0)
        for n, site in enumerate(Site.objects.all()):
            self.draw_progress_bar(float(n) / num_sites)
            update_site_covariates(site)
            if n % throttle == 0:
                sleep(1)

        self.draw_progress_bar(1)
