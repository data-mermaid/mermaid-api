import csv
import shutil
import sys
from tempfile import NamedTemporaryFile
from time import sleep
from .progress_bar_base_command import ProgressBarBaseCommand
from api.covariates.coral_atlas import CoralAtlasCovariate


LAT = "latitude"
LON = "longitude"


def notnull(val):
    if val and val != "" and val.upper() != "NA":
        return True
    return False


class Command(ProgressBarBaseCommand):
    help = "Populate ACA covariates for arbitrary lat/lons in a CSV file."

    def add_arguments(self, parser):
        parser.add_argument("datafile")
        parser.add_argument(
            "--simple",
            action="store_true",
            help="Captures and outputs only the name of the covariate with the largest area.",
        )
        parser.add_argument(
            "-r",
            "--radius",
            type=float,
            default=0.025,
            help="radius of buffer around point from which to extract covariate values",
        )
        parser.add_argument(
            "--throttle",
            type=int,
            default=50,
            help="Number of sites to fetch before sleeping 1 second.",
        )

    def handle(self, *args, **options):
        datafile = options["datafile"]
        simple = options["simple"]
        radius = options["radius"]
        throttle = options["throttle"]
        tempfile = NamedTemporaryFile(mode="w", delete=False)
        coral_atlas = CoralAtlasCovariate(radius=radius)

        with open(datafile, "r") as csvfile, tempfile:
            reader = csv.DictReader(csvfile)
            fieldnames = reader.fieldnames
            rows = list(reader)
            num_rows = len(rows)
            writer = csv.DictWriter(tempfile, fieldnames=fieldnames)
            writer.writeheader()

            self.draw_progress_bar(0)
            for n, row in enumerate(rows):
                self.draw_progress_bar(float(n) / num_rows)
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
                if n % throttle == 0:
                    sleep(1)
            sys.stdout.write("\n")

        shutil.move(tempfile.name, datafile)
