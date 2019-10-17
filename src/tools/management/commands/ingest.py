import argparse
import sys
import uuid

from django.core.management.base import BaseCommand, CommandError
from django.template.defaultfilters import pluralize

from api.ingest.utils import ingest_benthicpit, ingest_fishbelt
from api.models import (
    BENTHICLIT_PROTOCOL,
    BENTHICPIT_PROTOCOL,
    BLEACHINGQC_PROTOCOL,
    FISHBELT_PROTOCOL,
    HABITATCOMPLEXITY_PROTOCOL,
)

protocol_ingests = {
    BENTHICLIT_PROTOCOL: None,
    BENTHICPIT_PROTOCOL: ingest_benthicpit,
    FISHBELT_PROTOCOL: ingest_fishbelt,
    HABITATCOMPLEXITY_PROTOCOL: None,
    BLEACHINGQC_PROTOCOL: None,
}


class Command(BaseCommand):
    help = "Ingest collect records from CSV file."

    def add_arguments(self, parser):
        parser.add_argument("datafile", nargs=1, type=argparse.FileType("r"))
        parser.add_argument("project", nargs=1, type=uuid.UUID)
        parser.add_argument("profile", nargs=1, type=uuid.UUID)
        parser.add_argument("--protocol", choices=protocol_ingests.keys())
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Runs ingest in a database transaction, then does a rollback.",
        )

    def handle(self, datafile, project, profile, protocol, dry_run, *args, **options):
        datafile = datafile[0]
        project = project[0]
        profile = profile[0]
        verbosity = options["verbosity"]

        _ingest = protocol_ingests.get(protocol)

        if _ingest is None:
            raise NotImplementedError()

        records, errors = _ingest(datafile, project, profile, protocol, dry_run)

        if errors:
            if verbosity > 0:
                for err in errors:
                    self.stdout.write(err)

            if verbosity > 1:
                num_errors = len(errors)
                msg = "{} {} errors".format(
                    num_errors, pluralize(num_errors, "record has,records have")
                )
                self.stderr.write(msg)
            sys.exit(1)

        if dry_run:
            msg = "[DRYRUN] {} records would have been created.".format(len(records))
        else:
            msg = "{} records created.".format(len(records))

        if verbosity > 1:
            self.stdout.write(self.style.SUCCESS(msg))

        sys.exit(0)
