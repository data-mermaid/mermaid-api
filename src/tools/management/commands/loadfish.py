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
            type=argparse.FileType("r", encoding="windows-1252"),
            nargs="?",
            help="Fish species data CSV file",
        )

    def handle(self, fishdata, dry_run, **options):
        try:
            ingester = FishIngester(fishdata)
            _, logs = ingester.ingest(dry_run)
            for log in logs:
                print(f"{log}")
        finally:
            fishdata.close()
