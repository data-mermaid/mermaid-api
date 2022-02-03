import sys
from django.core.management.base import BaseCommand


class ProgressBarBaseCommand(BaseCommand):
    def draw_progress_bar(self, percent, bar_len=20):
        # percent float from 0 to 1.s
        sys.stdout.write("\r")
        symbols = "=" * int(bar_len * percent)
        sys.stdout.write(f"[{symbols:<{bar_len}}] {percent * 100:.0f}%")
        sys.stdout.flush()

        if percent == 1:
            print("")
