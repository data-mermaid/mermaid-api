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


class FishIngester(object):
    ERROR = "ERROR"
    EXISTING_FAMILY = "EXISTING_FAMILY"
    NEW_FAMILY = "NEW_FAMILY"
    DUPLICATE_FAMILY = "DUPLICATE_FAMILY"

    EXISTING_GENUS = "EXISTING_GENUS"
    NEW_GENUS = "NEW_GENUS"
    DUPLICATE_GENUS = "DUPLICATE_GENUS"
    MOVED_GENUS = "MOVED_GENUS"

    EXISTING_SPECIES = "EXISTING_SPECIES"
    NEW_SPECIES = "NEW_SPECIES"
    DUPLICATE_SPECIES = "DUPLICATE_SPECIES"
    MOVED_SPECIES = "MOVED_SPECIES"

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
    }

    def __init__(self, file_obj):
        self.log = []

        # Placeholders until needed
        self.fish_family_lookups = dict()
        self.fish_genus_lookups = dict()

        self.fish_species_lookups = self._create_fish_species_lookups()

        self._file = file_obj

    def _create_fish_species_lookups(self):
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

    def _map_fields(self, record, field_map, lookups=None):
        lookups = lookups or dict()
        mapped_rec = {}

        for k, v in record.items():
            if k not in field_map:
                continue
            elif field_map[k] in lookups:
                mapped_rec[field_map[k]] = lookups[field_map[k]].get(v)
            else:
                mapped_rec[field_map[k]] = v

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
        except FishGenus.DoesNotExist:
            genus = FishGenus.objects.create(family=fish_family, **genus_row)
            self.write_log(self.NEW_GENUS, genus_name)
        except FishGenus.MultipleObjectsReturned:
            self.write_log(self.DUPLICATE_GENUS, genus_name)

        return genus

    def _ingest_fish_species(self, row, fish_genus):
        species_row = self._map_fields(
            row, self.fish_species_field_map, self.fish_species_lookups
        )
        species_name = species_row["name"]
        genus_name = fish_genus.name
        try:
            species = FishSpecies.objects.get(name__iexact=species_name, genus=fish_genus)
            has_edits = False
            for k, v in species_row.items():
                if hasattr(species, k) and getattr(species, k) != v:
                    setattr(species, k, v)
                    has_edits = True

            if has_edits:
                species.save()

        except FishSpecies.DoesNotExist:
            species = FishSpecies.objects.create(genus=fish_genus, **species_row)
            self.write_log(self.NEW_SPECIES, f"{genus_name}-{species_name}")
        except FishSpecies.MultipleObjectsReturned:
            self.write_log(self.DUPLICATE_SPECIES, species_name)


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
        # parser.add_argument(
        #     "--mode", type=str, nargs="?", choices=["f", "g", "s", "d"], default="f"
        # )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Runs load fish in a database transaction, then does a rollback.",
        )

        parser.add_argument(
            "--config",
            type=argparse.FileType("r"),
            nargs="?",
            dest="config",
            action=JSONFileAction,
        )

        parser.add_argument(
            "fishdata",
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

    def handle(self, fishdata, dry_run, **options):
        try:
            ingester = FishIngester(fishdata)
            is_successful, logs = ingester.ingest(dry_run)
            for log in logs:
                print(f"{log}")
        finally:
            fishdata.close()
        #     with transaction.atomic():
        #         sid = transaction.savepoint()
        #         try:
        #             ingester = FishIngester(fishdata)
        #             is_successful, logs = ingester.ingest()
        #             for log in logs:
        #                 print(f"{log}")
        #             if dry_run or is_successful is False:
        #                 transaction.savepoint_rollback(sid)
        #             else:
        #                 transaction.savepoint_commit(sid)
        #         except Exception as err:
        #             transaction.savepoint_rollback(sid)
        #             self.stderr.write(str(err))
        #             sys.exit(1)
        # finally:
        #     fishdata.close()
