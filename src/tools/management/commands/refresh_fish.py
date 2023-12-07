import csv
import os
from contextlib import closing

import requests
from django.conf import settings
from django.core.management.base import BaseCommand

from api.models import (
    APPROVAL_STATUSES,
    BaseAttributeModel,
    FishFamily,
    FishGenus,
    FishGroupFunction,
    FishGroupSize,
    FishGroupTrophic,
    FishSpecies,
)

# from .refresh_base import get_regions


def map_fields(record, field_map):
    mapped_rec = {}
    for k, v in record.items():
        if k in field_map:
            mapped_rec[field_map[k]] = v
    mapped_rec["status"] = APPROVAL_STATUSES[0][0]
    return mapped_rec


def nullsafefloat(val, rounded=None):
    try:
        val = float(val)
        if rounded is not None:
            val = round(val, rounded)
    except (ValueError, TypeError):
        val = None
    return val


class Command(BaseCommand):
    help = """Insert or update fish attribute data from csv."""

    FISH_FAMILY_FIELD_MAP = {
        "Family": "name",
    }
    FISH_GENUS_FIELD_MAP = {
        "Genus": "name",
    }
    FISH_SPECIES_FIELD_MAP = {
        "Species": "name",
        "a": "biomass_constant_a",
        "b": "biomass_constant_b",
        "c": "biomass_constant_c",
        "Vulnerability": "vulnerability",
        "Trophic_level": "trophic_level",
        "Maxlength": "max_length",
        "Max_length_type": "max_length_type",
        "Trophic_group": "trophic_group",
        "Primary_functional_group": "functional_group",
        "Group_size": "group_size",
    }
    GROUP_SIZE_DATA_MAP = {
        "Sol": "solitary",
        "Pair": "pair",
        "SmallG": "small group",
        "MedG": "medium group",
        "LargeG": "large group",
    }
    LENGTH_TYPE_DATA_MAP = {
        "FL": "fork length",
        "SL": "standard length",
        "TL": "total length",
        "WD": "wing diameter",
    }
    TROPHIC_GROUP_DATA_MAP = {
        "FC": "piscivore",
        "HD": "herbivore-detritivore",
        "HM": "herbivore-macroalgae",
        "IM": "invertivore-mobile",
        "IS": "invertivore-sessile",
        "OM": "omnivore",
        "PK": "planktivore",
    }

    def __init__(self):
        super(Command, self).__init__()
        # self.source = 'http://datamermaid.org/listab_2018_August_data.csv'
        self.source = os.path.join(settings.BASE_DIR, "data", "listab_2018_August_data.csv")

    def handle(self, *args, **options):
        func_groups = {g.name: g.name for g in FishGroupFunction.objects.all()}

        # with closing(requests.get(self.source, stream=True)) as fishdata:
        with open(self.source) as fishdata:
            n = 0
            # csvreader = csv.DictReader(fishdata.iter_lines(), delimiter=',')
            csvreader = csv.DictReader(fishdata, delimiter=",")
            for row in csvreader:
                family_row = map_fields(row, self.FISH_FAMILY_FIELD_MAP)
                genus_row = map_fields(row, self.FISH_GENUS_FIELD_MAP)
                species_row = map_fields(row, self.FISH_SPECIES_FIELD_MAP)

                family_row["status"] = APPROVAL_STATUSES[0][0]
                family, _ = FishFamily.objects.get_or_create(**family_row)
                genus_row["family"] = family
                genus_row["status"] = APPROVAL_STATUSES[0][0]
                genus, _ = FishGenus.objects.get_or_create(**genus_row)
                species_row["genus"] = genus

                species_row["trophic_level"] = nullsafefloat(species_row["trophic_level"], 2)
                species_row["vulnerability"] = nullsafefloat(species_row["vulnerability"], 2)
                species_row["max_length"] = nullsafefloat(species_row["max_length"], 2)

                species_row["group_size"] = self.GROUP_SIZE_DATA_MAP.get(species_row["group_size"])
                if species_row["group_size"] is not None:
                    group_size, _ = FishGroupSize.objects.get_or_create(
                        name=species_row["group_size"]
                    )
                    species_row["group_size"] = group_size
                else:
                    species_row["group_size"] = None

                species_row["max_length_type"] = self.LENGTH_TYPE_DATA_MAP.get(
                    species_row["max_length_type"]
                )
                if species_row["max_length_type"] is None:
                    species_row["max_length_type"] = ""

                species_row["trophic_group"] = self.TROPHIC_GROUP_DATA_MAP.get(
                    species_row["trophic_group"]
                )
                if species_row["trophic_group"] is not None:
                    trophic_group, _ = FishGroupTrophic.objects.get_or_create(
                        name=species_row["trophic_group"]
                    )
                    species_row["trophic_group"] = trophic_group
                else:
                    species_row["trophic_group"] = None

                if "functional_group" in species_row and species_row["functional_group"] != "NA":
                    species_functionalgroup_name = func_groups[
                        species_row["functional_group"].lower()
                    ]
                    functional_group, _ = FishGroupFunction.objects.get_or_create(
                        name=species_functionalgroup_name
                    )
                    species_row["functional_group"] = functional_group
                else:
                    species_row["functional_group"] = None

                if "climate_score" not in species_row or species_row["climate_score"] == "NA":
                    species_row["climate_score"] = None

                # chosen_regions = get_regions(row['region'])
                species_row.pop("region", None)
                species_row["status"] = APPROVAL_STATUSES[0][0]
                # This version of refresh_fish relies on:
                # 1. using fish_update_working to ensure families/genera integrity
                # 2. using fish_update_working to check species spelling/other changes and validate new ones
                # 3. 'same' uses only name and genus; all other species attributes will be overwritten from csv
                # 4. duplicate species pre-cleaned
                fs, _ = FishSpecies.objects.get_or_create(
                    **{"name": species_row["name"], "genus": genus}
                )
                for attr, value in species_row.iteritems():
                    setattr(fs, attr, value)
                fs.save()
                # fs.regions.add(*chosen_regions)

                n += 1

            print("%s fish attributes rows\n" % (n - 1))
