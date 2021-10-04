import sys
from time import sleep

from django.core.management.base import BaseCommand

from api.covariates import update_site_covariates
from api.models import Profile


class ProgressBarBaseCommand(BaseCommand):
    def draw_progress_bar(self, percent, bar_len=20):
        # percent float from 0 to 1.s
        sys.stdout.write("\r")
        symbols = "=" * int(bar_len * percent)
        sys.stdout.write(f"[{symbols:<{bar_len}}] {percent * 100:.0f}%")
        sys.stdout.flush()

        if percent == 1:
            print("")
