from django.core.management.base import BaseCommand
from api.models import BeltTransectWidth


belt_transect_widths = (
    {
        'id': 'ab438b26-1ddf-4f62-b683-75dd364e614b',
        'val': 1
    },
    {
        'id': 'ab438b26-1ddf-4f62-b683-75dd364e614b',
        'val': 5
    },
    {
        'id': 'ab438b26-1ddf-4f62-b683-75dd364e614b',
        'val': 10
    },
)


def load_belt_fish_widths():
    n = 0
    for btw in belt_transect_widths:
        try:
            _ = BeltTransectWidth.objects.get(id=btw['id'])
        except:
            _ = BeltTransectWidth.objects.create(**btw)
            n += 1
    return n


class Command(BaseCommand):
    help = """Insert or update application choices.
    Does NOT overwrite existing data."""

    def handle(self, *args, **options):
        count = load_belt_fish_widths()
        print('{} belt fish widths added'.format(count))
