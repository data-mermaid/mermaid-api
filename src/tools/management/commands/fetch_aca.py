import csv
import shutil
from tempfile import NamedTemporaryFile
from django.core.management.base import BaseCommand
from api.covariates.coral_atlas import CoralAtlasCovariate


LAT = "latitude"
LON = "longitude"


def notnull(val):
    if val and val != "" and val.upper() != "NA":
        return True
    return False


class Command(BaseCommand):
    help = "Populate ACA covariates for arbitrary lat/lons in a CSV file."

    def add_arguments(self, parser):
        parser.add_argument("datafile")
        parser.add_argument(
            "--simple",
            action="store_true",
            help="Runs ingest in a database transaction, then does a rollback.",
        )

    def handle(self, datafile, simple, *args, **options):
        tempfile = NamedTemporaryFile(mode='w', delete=False)
        coral_atlas = CoralAtlasCovariate()

        with open(datafile, 'r') as csvfile, tempfile:
            reader = csv.DictReader(csvfile)
            fieldnames = reader.fieldnames
            writer = csv.DictWriter(tempfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in reader:
                if notnull(row[LAT]) and notnull(row[LON]):
                    results = coral_atlas.fetch([(float(row[LON]), float(row[LAT]))])
                    geomorphic = results[0]["covariates"]["aca_geomorphic"]
                    benthic = results[0]["covariates"]["aca_benthic"]

                    if geomorphic and "aca_geomorphic" in row:
                        row["aca_geomorphic"] = geomorphic
                        if simple:
                            sorted(geomorphic, key=lambda x: (x["area"]), reverse=True)
                            row["aca_geomorphic"] = geomorphic[0]["name"]
                    if benthic and "aca_benthic" in row:
                        row["aca_benthic"] = benthic
                        if simple:
                            sorted(benthic, key=lambda x: (x["area"]), reverse=True)
                            row["aca_benthic"] = benthic[0]["name"]

                writer.writerow(row)

        shutil.move(tempfile.name, datafile)
