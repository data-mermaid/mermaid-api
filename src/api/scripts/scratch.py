import json
import uuid
import pandas as pd

# from api.summaries import base
from api.summaries import beltfish
from api.utils.timer import timing
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.gis.geos import Point


PROJECT_ID = "95e0ffc7-3a7d-4538-953d-b35225dfa81a"
# PROJECT_ID = "75ef7a5a-c770-4ca6-b9f8-830cab74e425"



class ExtendedEncoder(DjangoJSONEncoder):
    def default(self, o):
        if isinstance(o, Point):
            # Convert the Point object to a geojson representation
            return {'type': 'Point', 'coordinates': [o.x, o.y]}
        return super().default(o)


@timing
def run():
    # beltfish_obs = beltfish.beltfish_obs(PROJECT_ID)
    # fish_trophic_group = beltfish.fish_trophic_group()
    # fish_families = beltfish.fish_families()

    # family_all = beltfish.beltfish_su_family_all(PROJECT_ID)
    # print(f"family_all: {family_all}")
    
    # belfish_su_family = beltfish.belfish_su_family(PROJECT_ID)
    # print(f"belfish_su_family: {belfish_su_family}")
    
    # beltfish_families = beltfish.beltfish_families(PROJECT_ID)
    # print(f"beltfish_families: {beltfish_families}")
    
    # beltfish_observers = beltfish.beltfish_observers(PROJECT_ID)
    # print(f"beltfish_observers: {beltfish_observers}")
    
    # beltfish_tg = beltfish.beltfish_tg(PROJECT_ID)
    # print(f"beltfish_tg: {beltfish_tg}")
    
    
    here = beltfish.here(PROJECT_ID)
    print(f"here: {here}")

    for k in here.keys():
        print(k)