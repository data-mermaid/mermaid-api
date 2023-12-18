from django.core.management.base import BaseCommand

from api.models import FishSize, FishSizeBin


def intervals(max_val, step):
    ranges = []
    medians = []
    for i in range(0, max_val, step):
        rng = [i, i + step]
        ranges.append(rng)
        medians.append(sum(rng) / 2.0)

    return ranges, medians


def create_records(ranges, medians, fish_bin):
    n = 0
    for r, m in zip(ranges, medians):
        _, created = FishSize.objects.get_or_create(
            fish_bin_size=fish_bin, val=m, name="{} - {}".format(*r)
        )
        if created is True:
            n += 1
    return n


class Command(BaseCommand):
    help = """Insert or update fish attribute data from csv.
    Does NOT overwrite existing data."""

    def handle(self, *args, **options):
        count = 0
        fish_bin_5 = FishSizeBin.objects.get(val="5")
        ranges_5, medians_5 = intervals(200, 5)
        count += create_records(ranges_5, medians_5, fish_bin_5)

        fish_bin_10 = FishSizeBin.objects.get(val="10")
        ranges_10, medians_10 = intervals(200, 10)
        count += create_records(ranges_10, medians_10, fish_bin_10)

        print("%s fish sizes\n" % (count))
