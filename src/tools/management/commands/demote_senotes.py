from django.core.management.base import BaseCommand

from api.models.mermaid import SampleEvent
from api.utils.notes import senotes2sunotes


class Command(BaseCommand):
    help = """Move (concatenate) SE notes to constituent SUs, then remove SE notes.
    Use --dryrun (or -d) option to test first.
    """

    def __init__(self):
        super(Command, self).__init__()
        self.dryrun = False
        self.id = False

    def add_arguments(self, parser):
        parser.add_argument(
            "-d",
            "--dryrun",
            action="store_true",
            default=False,
            help="Print affected SEs/SUs instead of committing db changes.",
        )
        parser.add_argument(
            "id", nargs="?", default=False, help="Only process sample event with this id"
        )

    def handle(self, *args, **options):
        self.dryrun = options.get("dryrun")
        self.id = options.get("id")

        sample_events = SampleEvent.objects.all()
        if self.id:
            sample_events = sample_events.filter(pk=self.id)
        for se in sample_events:
            senotes2sunotes(se, self.dryrun)
