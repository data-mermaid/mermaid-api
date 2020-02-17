import argparse

from django.core.management.base import BaseCommand

from api.ingest import BenthicIngester


class Command(BaseCommand):
    help = """
    Load benthic attributes from csv file
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Runs load benthic in a database transaction, then does a rollback.",
        )

        parser.add_argument(
            "benthicdata",
            type=argparse.FileType("r"),
            nargs="?",
            help="Fish species data CSV file",
        )

    def handle(self, benthicdata, dry_run, **options):
        try:
            ingester = BenthicIngester(benthicdata)
            _, logs = ingester.ingest(dry_run)
            for log in logs:
                print(f"{log}")
        finally:
            benthicdata.close()
