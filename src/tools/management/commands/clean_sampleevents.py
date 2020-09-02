from django.core.management.base import BaseCommand
from api.utils.sample_units import consolidate_sample_events


class Command(BaseCommand):
    help = """Find and remove orphan and duplicate sample events.
    Use --dryrun (or -d) option to test first.
    """

    def __init__(self):
        super(Command, self).__init__()
        self.dryrun = False

    def add_arguments(self, parser):
        parser.add_argument("-d", "--dryrun", action="store_true", default=False,
                            help="Run all cleanup queries inside a transaction that is rolled back")

    def handle(self, *args, **options):
        self.dryrun = options.get("dryrun")
        consolidate_sample_events(self.dryrun)
