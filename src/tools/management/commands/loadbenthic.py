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

from api.models import BenthicAttribute, Region, APPROVAL_STATUSES


class BenthicIngester(object):
    ERROR = "ERROR"
    EXISTING_BENTHIC = "EXISTING_BENTHIC"
    NEW_BENTHIC = "NEW_BENTHIC"
    DUPLICATE_BENTHIC = "DUPLICATE_BENTHIC"
    UPDATE_BENTHIC = "UPDATE_BENTHIC"

    approval_status = APPROVAL_STATUSES[0][0]

    benthic_field_map = {"level1": "level1", "level2": "level2", "level3": "level3", "regions": "regions"}

    def __init__(self, file_obj):
        self.log = []
        self.benthic_lookups = self._create_benthic_lookups()
        self.regions = {r.name.lower(): r for r in Region.objects.all()}
        self._file = file_obj

    def _create_benthic_lookups(self):
        return dict()

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

    def _ingest_benthic(self, row):
        benthic_row = self._map_fields(
            row, self.benthic_field_map, self.benthic_lookups
        )

        region_names = benthic_row.get("regions")
        level1 = benthic_row.get("level1")
        level2 = benthic_row.get("level2")
        level3 = benthic_row.get("level3")

        if not level1:
            return

        try:
            parent1 = BenthicAttribute.objects.get(name__iexact=level1)
            self.write_log(self.EXISTING_BENTHIC, f"Parent level 1 - {parent1}")
        except BenthicAttribute.DoesNotExist:
            parent1 = BenthicAttribute.objects.create(name=level1)
            self.write_log(self.NEW_BENTHIC, f"Parent level 1 - {parent1}")

        self._update_regions(parent1, region_names)

        if not level2:
            return

        try:
            parent2 = BenthicAttribute.objects.get(name__iexact=level2, parent=parent1)
            self.write_log(self.EXISTING_BENTHIC, f"Parent level 2 - {parent2}")
        except BenthicAttribute.DoesNotExist:
            parent2 = BenthicAttribute.objects.create(name=level2, parent=parent1)
            self.write_log(self.NEW_BENTHIC, f"Parent level 2 - {parent2}")

        self._update_regions(parent2, region_names)

        if not level3:
            return

        try:
            parent3 = BenthicAttribute.objects.get(name__iexact=level3, parent=parent2)
            self.write_log(self.EXISTING_BENTHIC, f"Parent level 3 - {parent3}")
        except BenthicAttribute.DoesNotExist:
            parent3 = BenthicAttribute.objects.create(name=level3, parent=parent2)
            self.write_log(self.NEW_BENTHIC, f"Parent level 3 - {parent3}")

        self._update_regions(parent3, region_names)

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
                    self._ingest_benthic(row)

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

    def _update_regions(self, benthic, region_names):
        new_regions = [
            self.regions.get(region.strip().lower())
            for region in region_names.split(",")
        ]

        if set(benthic.regions.all()) == set(new_regions):
            return False

        benthic.regions.clear()
        benthic.regions.set(new_regions)
        return True


class Command(BaseCommand):
    help = """

    """

    def __init__(self):
        super(Command, self).__init__()

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Runs load benthic in a database transaction, then does a rollback.",
        )

        parser.add_argument(
            "benthicdata",
            type=argparse.FileType("r", encoding="windows-1252"),
            nargs="?",
            help="Fish species data CSV file",
        )

    def handle(self, benthicdata, dry_run, **options):
        try:
            ingester = BenthicIngester(benthicdata)
            is_successful, logs = ingester.ingest(dry_run)
            for log in logs:
                print(f"{log}")
        finally:
            benthicdata.close()
