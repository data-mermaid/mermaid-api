import argparse
import os
import json
import requests
import csv
import sys
import datetime

from contextlib import closing
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.db.models import fields

from api.models import (
    FishFamily,
    FishGenus,
    FishSpecies,
    FishGroupSize,
    FishGroupTrophic,
    FishGroupFunction,
    Region,
    APPROVAL_STATUSES,
)
from api.utils import castutils


class FishIngester(object):
    ERROR = "ERROR"
    EXISTING_FAMILY = "EXISTING_FAMILY"
    NEW_FAMILY = "NEW_FAMILY"

    EXISTING_GENUS = "EXISTING_GENUS"
    NEW_GENUS = "NEW_GENUS"
    DUPLICATE_GENUS = "DUPLICATE_GENUS"

    EXISTING_SPECIES = "EXISTING_SPECIES"
    NEW_SPECIES = "NEW_SPECIES"
    DUPLICATE_SPECIES = "DUPLICATE_SPECIES"
    UPDATE_SPECIES = "UPDATE_SPECIES"

    approval_status = APPROVAL_STATUSES[0][0]

    fish_family_field_map = {"Family": "name"}

    fish_genus_field_map = {"Genus": "name"}

    fish_species_field_map = {
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
        "regions": "regions",
    }

    def __init__(self, file_obj):
        self.log = []

        # Placeholders until needed
        self.fish_family_lookups = dict()
        self.fish_genus_lookups = dict()

        self.fish_species_lookups = self._create_fish_species_lookups()
        self.regions = {r.name.lower(): r for r in Region.objects.all()}
        self.fish_species_casts = self._get_model_casts(FishSpecies)

        self._file = file_obj

    def _get_model_casts(self, model_cls):
        fields = model_cls._meta.get_fields()
        casts = dict()

        for field in fields:

            if field.get_internal_type() == "DecimalField":
                kwargs = dict(max_digits=field.max_digits, precision=field.decimal_places)
                casts[field.name.lower()] = dict(
                    fx=castutils.to_decimal, kwargs=kwargs
                )

        return casts

    def _create_fish_species_lookups(self):
        fish_group_sizes = {
            fg.name.lower(): fg for fg in FishGroupSize.objects.all()
        }
        fish_group_trophics = {
            fgt.name.lower(): fgt for fgt in FishGroupTrophic.objects.all()
        }
        fish_group_functions = {
            fgf.name.lower(): fgf for fgf in FishGroupFunction.objects.all()
        }

        return dict(
            group_size=fish_group_sizes,
            trophic_group=fish_group_trophics,
            functional_group=fish_group_functions,
        )

    def _map_fields(self, record, field_map, lookups=None, casts=None):
        lookups = lookups or dict()
        casts = casts or dict()
        mapped_rec = {}

        for k, v in record.items():
            mapped_key = field_map.get(k)
            if mapped_key is None:
                continue
            elif mapped_key in lookups:
                if v:
                    val = lookups[field_map[k]][v]
                else:
                    val = v
            else:
                val = v

            if mapped_key in casts:
                cast = casts.get(mapped_key)
                kwargs = cast.get("kwargs") or dict()
                val = cast["fx"](val, **kwargs)

            mapped_rec[field_map[k]] = val

        mapped_rec["status"] = self.approval_status
        return mapped_rec

    def write_log(self, action, message):
        timestamp = datetime.datetime.now().isoformat()
        log_msg = f"{action} [{timestamp}] {message}"
        self.log.append(log_msg)

    def ingest(self, dry_run=False):
        self.log = []
        csvreader = csv.DictReader(self._file, delimiter=",")
        n = 2
        is_successful = True
        for row in csvreader:
            try:
                with transaction.atomic():
                    sid = transaction.savepoint()
                    fish_family = self._ingest_fish_family(row)
                    fish_genus = self._ingest_fish_genus(row, fish_family=fish_family)
                    self._ingest_fish_species(row, fish_genus=fish_genus)

                    if dry_run or is_successful is False:
                        transaction.savepoint_rollback(sid)
                    else:
                        transaction.savepoint_commit(sid)

            except Exception as err:
                transaction.savepoint_rollback(sid)
                err_msg = f"Row {n} - {str(err)}"
                self.write_log(self.ERROR, err_msg)
                is_successful = False
            finally:
                n = n + 1

        return is_successful, self.log

    def _ingest_fish_family(self, row):
        family_row = self._map_fields(
            row, self.fish_family_field_map, self.fish_family_lookups
        )
        family_name = family_row.get("name")

        fish_family = None
        try:
            fish_family = FishFamily.objects.get(name__iexact=family_name)
            self.write_log(self.EXISTING_FAMILY, family_name)
        except FishFamily.DoesNotExist:
            fish_family = FishFamily.objects.create(**family_row)
            self.write_log(self.NEW_FAMILY, family_name)
        except FishFamily.MultipleObjectsReturned:
            self.write_log(self.DUPLICATE_FAMILY, family_name)

        return fish_family

    def _ingest_fish_genus(self, row, fish_family):
        genus_row = self._map_fields(
            row, self.fish_genus_field_map, self.fish_genus_lookups
        )
        genus_name = genus_row["name"]
        try:
            genus = FishGenus.objects.get(name__iexact=genus_name, family=fish_family)
            self.write_log(self.EXISTING_GENUS, genus_name)
        except FishGenus.DoesNotExist:
            genus = FishGenus.objects.create(family=fish_family, **genus_row)
            self.write_log(self.NEW_GENUS, genus_name)
        except FishGenus.MultipleObjectsReturned:
            self.write_log(self.DUPLICATE_GENUS, genus_name)

        return genus

    def _update_regions(self, species, region_names):
        new_regions = [
            self.regions.get(region.strip().lower())
            for region in region_names.split(",")
        ]

        if set(species.regions.all()) == set(new_regions):
            return False

        species.regions.clear()
        species.regions.set(new_regions)
        return True

    def _ingest_fish_species(self, row, fish_genus):
        species_row = self._map_fields(
            row,
            self.fish_species_field_map,
            lookups=self.fish_species_lookups,
            casts=self.fish_species_casts,
        )
        species_name = species_row["name"]
        genus_name = fish_genus.name
        try:
            species = FishSpecies.objects.get(
                name__iexact=species_name, genus=fish_genus
            )
            has_edits = False
            region_names = species_row.pop("regions")
            updates = []
            for k, v in species_row.items():
                original_val = getattr(species, k)
                if hasattr(species, k) and original_val != v:
                    setattr(species, k, v)
                    updates.append(f"{k}: {original_val} -> {v}")
                    has_edits = True

            has_region_edits = self._update_regions(species, region_names)
            if has_edits or has_region_edits:
                species.save()
                self.write_log(self.UPDATE_SPECIES, f"{genus_name}-{species_name}: {', '.join(updates)}")
            else:
                self.write_log(self.EXISTING_SPECIES, f"{genus_name}-{species_name}")

        except FishSpecies.DoesNotExist:
            region_names = species_row.pop("regions")
            species = FishSpecies.objects.create(genus=fish_genus, **species_row)
            self._update_regions(species, region_names)

            self.write_log(self.NEW_SPECIES, f"{genus_name}-{species_name}")
        except FishSpecies.MultipleObjectsReturned:
            self.write_log(self.DUPLICATE_SPECIES, species_name)


class Command(BaseCommand):
    help = """
    
    """

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
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Runs load fish in a database transaction, then does a rollback.",
        )

        parser.add_argument(
            "fishdata",
            type=argparse.FileType("r", encoding="windows-1252"),
            nargs="?",
            help="Fish species data CSV file",
        )

    def handle(self, fishdata, dry_run, **options):
        try:
            ingester = FishIngester(fishdata)
            is_successful, logs = ingester.ingest(dry_run)
            for log in logs:
                print(f"{log}")
        finally:
            fishdata.close()
