import argparse
import json
import sys
import uuid

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.template.defaultfilters import pluralize

from api.ingest.utils import get_protocol_ingest
from api.models import (
    BENTHICLIT_PROTOCOL,
    BENTHICPIT_PROTOCOL,
    BLEACHINGQC_PROTOCOL,
    FISHBELT_PROTOCOL,
    HABITATCOMPLEXITY_PROTOCOL,
    CollectRecord,
)


class Command(BaseCommand):
    help = "Ingest collect records from a CSV file."

    protocol_choices = (BENTHICPIT_PROTOCOL, FISHBELT_PROTOCOL)

    def add_arguments(self, parser):
        parser.add_argument("datafile", nargs=1, type=argparse.FileType("r"))
        parser.add_argument("project", nargs=1, type=uuid.UUID)
        parser.add_argument("profile", nargs=1, type=uuid.UUID)
        parser.add_argument("--protocol", choices=self.protocol_choices)
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Runs ingest in a database transaction, then does a rollback.",
        )
        parser.add_argument(
            "--clear-existing",
            action="store_true",
            help="Remove existing collect records for protocol before ingesting file",
        )

    def clear_collect_records(self, project, protocol):
        sql = """
            DELETE FROM {table_name}
            WHERE 
                project_id='{project}' AND 
                data->>'protocol' = '{protocol}';
            """.format(
            table_name=CollectRecord.objects.model._meta.db_table,
            project=project,
            protocol=protocol,
        )
        with connection.cursor() as cursor:
            cursor.execute(sql)
            return cursor.rowcount

    def handle(
        self,
        datafile,
        project,
        profile,
        protocol,
        dry_run,
        clear_existing,
        *args,
        **options
    ):
        datafile = datafile[0]
        project = project[0]
        profile = profile[0]
        verbosity = options["verbosity"]

        _ingest = get_protocol_ingest(protocol)

        if _ingest is None:
            raise NotImplementedError()

        try:
            with transaction.atomic():
                sid = transaction.savepoint()
                if clear_existing:
                    self.clear_collect_records(project, protocol)
                records, errors = _ingest(datafile, project, profile, dry_run)
                transaction.savepoint_commit(sid)
        except Exception as err:
            transaction.savepoint_rollback(sid)
            self.stderr.write(str(err))
            sys.exit(1)

        if errors:
            if verbosity > 0:
                for err in errors:
                    self.stdout.write(json.dumps(err))

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
