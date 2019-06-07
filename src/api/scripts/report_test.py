# from api.resources.obs_belt_fish import ObsBeltFishExtendedSerializer as OBFS
# from rest_framework.utils import encoders
# from api.utils import flatten
# import json
from api.reports import RawCSVReport
from api.models.mermaid import ObsBeltFish
from api.resources.obs_belt_fish import ObsBeltFishExtendedSerializer


def run():
    obfs = ObsBeltFish.objects.all()
    excluded_columns = [
        r'\.id$',
        r'updated_by$',
        r'updated_on$',
        r'created_on$',
        'beltfish',
        'fish_attribute\.status',
        'sample_event\.site\.location*',
        'fish_belt_transect\.sample_event',

    ]
    report = RawCSVReport(excluded_columns=excluded_columns)
    report.generate('test.csv', obfs, serializer_class=ObsBeltFishExtendedSerializer)
