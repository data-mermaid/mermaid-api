import argparse

from django.core.management.base import BaseCommand

from api.ingest import FishIngester


class Command(BaseCommand):
    help = """
    Load fish attributes from csv file
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Runs load fish in a database transaction, then does a rollback.",
        )

        parser.add_argument(
            "fishdata",
            type=argparse.FileType("r", encoding="utf-8-sig"),
            nargs="?",
            help="Fish species data CSV file",
        )

        parser.add_argument(
            "--allow-multiword-species",
            action="store_true",
            help="Skip the check that rejects species names containing spaces (e.g. subspecies).",
        )

    def handle(self, fishdata, dry_run, allow_multiword_species, **options):
        try:
            ingester = FishIngester(fishdata)
            _, logs = ingester.ingest(dry_run, allow_multiword_species=allow_multiword_species)
            for log in logs:
                print(f"{log}")
        finally:
            fishdata.close()
