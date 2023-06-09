import uuid
from collections import defaultdict
from api.models.mermaid import CollectRecord

OBS_KEYS = [
    "obs_benthic_lits",
    "obs_benthic_pits",
    "obs_benthic_photo_quadrats",
    "obs_colonies_bleached",
    "obs_belt_fishes",
    "obs_quadrat_benthic_percent",
    "obs_habitat_complexities",
]


def run():
    needed_update = defaultdict(int)

    for cr in CollectRecord.objects.all():
        obs = []
        obs_key = None
        for key in OBS_KEYS:
            try:
                obs = cr.data[key]
                obs_key = key
            except:
                continue

        if obs and obs_key:
            needs_update = False
            for o in obs:
                if "id" not in o:
                    needs_update = True
                    o["id"] = str(uuid.uuid4())

            if needs_update:
                needed_update[obs_key] += 1
                cr.save()

    for key in needed_update:
        print(f"{needed_update[key]} {key} CollectRecords updated")
