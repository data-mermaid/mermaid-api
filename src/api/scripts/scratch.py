from django.db import connection
from api.utils.summary_cache import update_summary_cache
from api.models import HABITATCOMPLEXITY_PROTOCOL


def run():
    # pk = "0f17035f-0683-4228-ba55-45f1653feb6e"
    pk = "dcc880fe-9621-41e9-a548-13268846651c"
    pk = "9bf0538e-99c7-405b-a54b-a1568c8a757e"
    # pk = "75ef7a5a-c770-4ca6-b9f8-830cab74e425"
    update_summary_cache(pk, HABITATCOMPLEXITY_PROTOCOL)
    # with Timer("Fetch Records"):
    #     _fetch_records2(BeltFishObsSQLModel, BeltFishObsModel, pk)
    # update_summary_cache(pk)
