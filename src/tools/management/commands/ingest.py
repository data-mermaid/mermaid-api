import argparse
import json
import sys
import uuid

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.template.defaultfilters import pluralize

from api.ingest.utils import ingest
from api.models import (
    BENTHICLIT_PROTOCOL,
    BENTHICPIT_PROTOCOL,
    BLEACHINGQC_PROTOCOL,
    FISHBELT_PROTOCOL,
    HABITATCOMPLEXITY_PROTOCOL,
    CollectRecord,
)
from api.resources.collect_record import CollectRecordSerializer
from api.submission.validations import ERROR, OK, WARN


class Command(BaseCommand):
    help = "Ingest collect records from a CSV file."

    protocol_choices = (BENTHICPIT_PROTOCOL, BLEACHINGQC_PROTOCOL, FISHBELT_PROTOCOL)

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

        parser.add_argument(
            "--validate",
            action="store_true",
            help="Validate ingested collect records",
        )

        parser.add_argument(
            "--validate-config",
            action="store",
            type=str,
            help="Validation config",
        )

        parser.add_argument(
            "--submit",
            action="store_true",
            help="Submit valid ingested collect records",
        )

    def _validation_summary(self, results):
        oks = 0
        warns = 0
        errors = 0
        for result in results:
            if result.get("status") == OK:
                oks += 1
            elif result.get("status") == WARN:
                warns += 1
            elif result.get("status") == ERROR:
                errors += 1

        return oks, warns, errors

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

        is_validate = options.get("validate")
        validate_config = None
        try:
            config = options.get("validate_config")
            if config:
                validate_config = json.loads(config)
        except (ValueError, TypeError):
            self.stderr.write("validate_config is invalid")
            sys.exit(1)

        is_submit = options.get("submit")

        if protocol is None:
            raise NotImplementedError()

        try:
            with transaction.atomic():
                sid = transaction.savepoint()
                try:
                    records, ingest_output = ingest(
                        protocol=protocol,
                        datafile=datafile,
                        project_id=project,
                        profile_id=profile,
                        request=None,
                        dry_run=dry_run,
                        clear_existing=clear_existing,
                        bulk_validation=is_validate,
                        bulk_submission=is_submit,
                        validation_suppressants=validate_config,
                        serializer_class=CollectRecordSerializer
                    )
                except InvalidSchema as schema_error:
                    missing_required_fields = schema_error.errors
                    transaction.savepoint_rollback(sid)
                    self.stderr.write(f"Missing required fields: {', '.join(missing_required_fields)}")
                    sys.exit(1)

                transaction.savepoint_commit(sid)
        except Exception as err:
            transaction.savepoint_rollback(sid)
            self.stderr.write(str(err))
            sys.exit(1)

        if "errors" in ingest_output:
            errors = ingest_output["errors"]
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

        if "validate" in ingest_output:
            validation_results = ingest_output["validate"]
            validation_oks, validation_warns, validation_errors = self._validation_summary(validation_results.values())

            if verbosity > 0:
                pass

            if verbosity > 1:
                self.stdout.write("\nCollect record validation results:")
                self.stdout.write(self.style.SUCCESS(f"Valid: {validation_oks}"))
                self.stdout.write(self.style.WARNING(f"Warnings: {validation_warns}"))
                self.stdout.write(self.style.ERROR(f"Errors: {validation_errors}"))

        if "submit" in ingest_output:
            submission_results = ingest_output["submit"]
            submission_oks, submission_warns, submission_errors = self._validation_summary(submission_results.values())

            if verbosity > 0:
                pass

            if verbosity > 1:
                self.stdout.write("\nCollect record submission results:")
                self.stdout.write(self.style.SUCCESS(f"Submitted: {validation_oks}"))
                self.stdout.write(self.style.WARNING(f"Warnings: {validation_warns}"))
                self.stdout.write(self.style.ERROR(f"Errors: {validation_errors}"))

        sys.exit(0)
