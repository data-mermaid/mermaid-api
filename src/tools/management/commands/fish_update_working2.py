import argparse
import os
import json
import requests
import csv
from contextlib import closing
from django.conf import settings
from django.core.management.base import BaseCommand

from api.models import (
    FishFamily,
    FishGenus,
    FishSpecies,
    FishGroupSize,
    FishGroupTrophic,
    FishGroupFunction,
    Region,
    BaseAttributeModel,
    APPROVAL_STATUSES,
)


def map_fields(record, field_map, lookups=None):
    lookups = lookups or dict()
    mapped_rec = {}
    for k, v in record.items():
        if k in field_map:
            mapped_rec[field_map[k]] = (
                lookups[field_map[k]].get(v) if field_map[k] in lookups else v
            )
    mapped_rec["status"] = APPROVAL_STATUSES[0][0]
    return mapped_rec


def create_key(data, keys):
    return ":::".join([data.get(k) or "" for k in sorted(keys)])


class JSONFileAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        try:
            dict_ = json.loads(values.read())
        except json.decoder.JSONDecodeError:
            dict_ = dict()

        setattr(namespace, self.dest, dict_)


class Command(BaseCommand):
    help = """Version of refresh_fish meant for ad hoc db querying/editing.
    Just uses names for determining new/update status; migrations for schema changes unnecessary."""

    FISH_FAMILY_FIELD_MAP = {"Family": "name"}
    FISH_GENUS_FIELD_MAP = {"Genus": "name"}
    FISH_SPECIES_FIELD_MAP = {
        "Species": "name",
        "a": "biomass_constant_a",
        "b": "biomass_constant_b",
        "c": "biomass_constant_c",
        "Vulnerability": "vulnerability",
        "Maxlength": "max_length",
        "Max_length_type": "max_length_type",
        "Trophic_group": "trophic_group",
        "Primary_functional_group": "functional_group",
        "Group_size": "group_size",
        "Trophic_level": "trophic_level",
    }

    def __init__(self):
        super(Command, self).__init__()

    def add_arguments(self, parser):
        # f = family
        # g = genus
        # s = species
        # d = delete
        parser.add_argument(
            "--mode", type=str, nargs="?", choices=["f", "g", "s", "d"], default="f"
        )
        parser.add_argument(
            "--config",
            type=argparse.FileType("r"),
            nargs="?",
            dest="config",
            action=JSONFileAction,
        )

        parser.add_argument(
            "data",
            type=argparse.FileType("r"),
            nargs="?",
            help="Fish species data CSV file",
        )

    def create_lookups(self):
        fish_group_sizes = {
            fg.pk: fg.name.lower() for fg in FishGroupSize.objects.all()
        }
        fish_group_trophics = {
            fgt.pk: fgt.name.lower() for fgt in FishGroupTrophic.objects.all()
        }
        fish_group_functions = {
            fgf.pk: fgf.name.lower() for fgf in FishGroupFunction.objects.all()
        }
        regions = {r.pk: r.name.lower() for r in Region.objects.all()}

        return dict(
            group_size=fish_group_sizes,
            trophic_group=fish_group_trophics,
            functional_group=fish_group_functions,
            region=regions,
        )

    def handle(self, **options):

        fishdata = options.get("data")
        mode = options.get("mode")
        config = options.get("config") or dict()

        fish_family_field_map = (
            config.get("fish_family_field_map") or self.FISH_FAMILY_FIELD_MAP
        )
        fish_genus_field_map = (
            config.get("fish_genus_field_map") or self.FISH_GENUS_FIELD_MAP
        )
        fish_species_field_map = (
            config.get("fish_species_field_map") or self.FISH_SPECIES_FIELD_MAP
        )

        lookups = self.create_lookups()

        # with closing(requests.get(self.source, stream=True)) as fishdata:
        try:
            csvreader = csv.DictReader(fishdata, delimiter=",")
            new_families = set()
            dup_families = set()
            new_genera = set()
            dup_genera = set()
            moved_genera = {}
            new_species = set()
            dup_species = set()
            moved_species = {}

            all_new_families = set()
            all_new_genera = set()
            all_new_species = set()

            for row in csvreader:
                family_row = map_fields(row, fish_family_field_map, lookups=lookups)
                family_name = family_row["name"]
                all_new_families.add(family_name)

                # FISH FAMILIES

                fish_family = None
                try:
                    fish_family = FishFamily.objects.get(name__iexact=family_name)
                except FishFamily.DoesNotExist:
                    fish_family = FishFamily.objects.create(**family_row)
                    new_families.add(family_row["name"])
                except FishFamily.MultipleObjectsReturned:
                    dup_families.add(family_name)

                # FISH GENERA

                genus_row = map_fields(row, fish_genus_field_map, lookups=lookups)
                genus_name = genus_row["name"]
                all_new_genera.add(genus_name)
                try:
                    genus = FishGenus.objects.get(name__iexact=genus_name)
                    if family_name != genus.family.name:
                        moved_genera[genus.pk] = (
                            genus.name,
                            genus.family.name,
                            family_name,
                        )
                except FishGenus.DoesNotExist:
                    genus = FishGenus.objects.create(family=fish_family, **genus_row)
                    new_genera.add(genus_name)
                except FishGenus.MultipleObjectsReturned:
                    dup_genera.add(genus_name)

                # FISH SPECIES

                species_row = map_fields(row, fish_species_field_map, lookups=lookups)
                species_name = species_row["name"]
                all_new_species.add(species_name)
                try:
                    species = FishSpecies.objects.get(
                        name__iexact=species_name, genus__name__iexact=genus_name
                    )
                    if genus_row["name"] != species.genus.name:
                        moved_species[species.pk] = (
                            species.name,
                            species.genus.name,
                            genus_row["name"],
                        )
                except FishSpecies.DoesNotExist:
                    print('species_row: {}'.format(species_row))
                    species = FishSpecies.objects.create(genus=genus, **species_row)
                    new_species.add(species_name)
                except FishSpecies.MultipleObjectsReturned:
                    dup_species.add(species_name)

            if mode == "f":
                print("\nnew_families:")
                print("\n".join(sorted(new_families)))
                print("\ndup_families:")
                print("\n".join(sorted(dup_families)))
            elif mode == "g":
                print("\nnew_genera:")
                print("\n".join(sorted(new_genera)))
                print("\ndup_genera:")
                print("\n".join(sorted(dup_genera)))
                print("\ngenera with changed family:")
                print(
                    "\n".join(
                        [self.moved_template % g for g in sorted(moved_genera.values())]
                    )
                )
            elif mode == "s":
                print("\nnew_species:")
                print("\n".join(sorted(new_species)))
                print("\ndup_species:")
                print("\n".join(sorted(dup_species)))
                print("\nspecies with changed genus:")
                print(
                    "\n".join(
                        [
                            self.moved_template % s
                            for s in sorted(moved_species.values())
                        ]
                    )
                )
            elif mode == "d":
                print("\nfamilies to delete:")
                for f in FishFamily.objects.all().values():
                    if f["name"] not in all_new_families:
                        print(f["name"])
                print("\ngenera to delete:")
                for g in FishGenus.objects.all().values():
                    if g["name"] not in all_new_genera:
                        print(g["name"])
                print("\nspecies to delete:")
                for s in FishSpecies.objects.all().values():
                    if s["name"] not in all_new_species:
                        print(s["name"])
        finally:
            fishdata.close()
