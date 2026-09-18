import contextlib
import gzip
import os
import re
import sys

import dateutil.parser
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone

from api.utils import s3

RECORDS_DIR = "records"
BACKUP_EXTENSION = "ndjson"
GZIP_EXTENSION = "gz"
DEFAULT_DATETIME_FIELD = "created_on"
DEFAULT_AGE_YEARS = 1
DELETE_BATCH_SIZE = 1000
CONTENT_TYPE = "application/x-ndjson"
GZIP_CONTENT_TYPE = "application/gzip"
GZIP_COMPRESS_LEVEL = 5
MAX_FILENAME_SUFFIX = 1000

# Table and column names are interpolated into SQL rather than parameterized, so they are
# restricted to plain unquoted identifiers and then checked against the catalog.
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def quote_identifier(name):
    if not IDENTIFIER_PATTERN.match(name):
        raise CommandError(f"'{name}' is not a valid unquoted SQL identifier")
    return f'"{name}"'


def is_datetime_type(data_type):
    """format_type output for a date/datetime column, e.g. 'timestamp with time zone',
    'timestamp(3) without time zone', 'date'."""
    return data_type == "date" or data_type.startswith("timestamp")


class Command(BaseCommand):
    help = """Back up a table's older records to a line-delimited JSON file, upload it to S3, and
    optionally delete the records that were backed up.

    Each line of the output file is one table record as a JSON object. Records are selected by a
    datetime field (default: created_on) and, by default, only records at least a year old are
    included. The file is gzipped as it is written unless --no-compress is given. If the
    destination name is already taken -- the S3 key, or the local file when --no-upload is given --
    the filename gets an incrementing '_N' suffix so an existing backup is never overwritten.

    Examples:
        # Back up api_archivedrecord rows created more than a year ago
        manage.py table_backup api_archivedrecord

        # Back up and then delete rows older than a specific date, filtered on a different field
        manage.py table_backup api_archivedrecord --datetime-field=updated_on \\
            --end-date=2024-01-01 --delete

    --delete reads and deletes in two steps rather than one transaction, so it is meant for
    records that are no longer being changed. A record whose datetime field is updated out of the
    backed up range in between is left alone, but a record whose other columns change in that
    window is still deleted, and the backup holds the version read at the start.

    The delete only runs once the uploaded object has been confirmed to be the same size as the
    local backup file, and it asks for confirmation first unless --noinput is given (which any
    scheduled or otherwise non-interactive run needs). Use --dry-run to report what a run would
    back up and delete without touching the table, the filesystem or S3.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pk_column = None

    def add_arguments(self, parser):
        parser.add_argument("table", type=str, help="Name of the table to back up")
        parser.add_argument(
            "--datetime-field",
            dest="datetime_field",
            default=DEFAULT_DATETIME_FIELD,
            help=f"Datetime column to filter on (default: {DEFAULT_DATETIME_FIELD})",
        )
        parser.add_argument(
            "--end-date",
            dest="end_date",
            type=dateutil.parser.isoparse,
            default=None,
            help=(
                "Back up records with a datetime field value earlier than this ISO date/datetime "
                f"(default: {DEFAULT_AGE_YEARS} year ago)"
            ),
        )
        parser.add_argument(
            "--start-date",
            dest="start_date",
            type=dateutil.parser.isoparse,
            default=None,
            help=(
                "Optional lower bound (inclusive) on the datetime field. Without it, all records "
                "older than --end-date are backed up."
            ),
        )
        parser.add_argument(
            "--delete",
            action="store_true",
            default=False,
            help="Delete the backed-up records after the backup has been uploaded successfully",
        )
        parser.add_argument(
            "-n",
            "--no-upload",
            action="store_true",
            dest="no_upload",
            default=False,
            help="Write the backup file locally but do not upload it to S3",
        )
        parser.add_argument(
            "--output-dir",
            dest="output_dir",
            default=os.path.join(os.path.sep, "tmp", "mermaid"),
            help="Local directory the backup file is written to",
        )
        parser.add_argument(
            "--no-compress",
            action="store_true",
            dest="no_compress",
            default=False,
            help=(
                f"Write plain {BACKUP_EXTENSION} instead of gzipping the backup "
                f"({BACKUP_EXTENSION}.{GZIP_EXTENSION})"
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            default=False,
            help=(
                "Report the records that would be backed up (and deleted, with --delete) and "
                "exit without writing, uploading or deleting anything"
            ),
        )
        parser.add_argument(
            "--noinput",
            "--no-input",
            action="store_false",
            dest="interactive",
            default=True,
            help="Do not prompt for confirmation before deleting; required for --delete when "
            "there is no terminal to prompt on",
        )
        parser.add_argument(
            "--keep-local",
            action="store_true",
            dest="keep_local",
            default=False,
            help="Keep the local backup file after it has been uploaded",
        )

    def handle(self, *args, **options):
        table = options["table"]
        datetime_field = options["datetime_field"]
        delete = options["delete"]
        no_upload = options["no_upload"]
        compress = not options["no_compress"]

        # Deleting records whose only backup is a local file on an ephemeral container would be
        # data loss, so the two flags are mutually exclusive.
        if delete and no_upload:
            raise CommandError("--delete cannot be used with --no-upload")

        self._validate_table(table)
        self._validate_datetime_field(table, datetime_field)
        # --delete needs a single-column primary key. Resolving it here rather than at delete
        # time means a table without one fails before the table is scanned and S3 is probed.
        if delete:
            self._get_pk_column(table)

        end_date = options["end_date"] or timezone.now() - relativedelta(years=DEFAULT_AGE_YEARS)
        start_date = options["start_date"]
        end_date = self._make_aware(end_date)
        start_date = self._make_aware(start_date)
        if start_date and start_date >= end_date:
            raise CommandError(f"--start-date ({start_date}) must be earlier than --end-date")

        where_sql, where_params = self._build_where(datetime_field, start_date, end_date)

        record_count, min_value, max_value = self._summarize(
            table, datetime_field, where_sql, where_params
        )
        if record_count == 0:
            self.stdout.write(f"No records in {table} match the filter; nothing to back up")
            return

        self.stdout.write(
            f"{record_count} record(s) in {table} with "
            f"{datetime_field} from {min_value} to {max_value}"
        )

        # The filename bounds describe the data actually in the file, so an open-ended backup
        # gets the earliest value present rather than a placeholder.
        stem = self._build_stem(table, start_date or min_value, end_date)
        extension = self._build_extension(compress)

        if options["dry_run"]:
            self._report_dry_run(
                table, record_count, stem, extension, options["output_dir"], no_upload, delete
            )
            return

        # Asked before anything is written or uploaded, so cancelling leaves no partial work and
        # a mistyped --end-date is caught while the range is still on screen.
        if delete and options["interactive"]:
            self._confirm_delete(table, datetime_field, record_count, min_value, max_value)

        os.makedirs(options["output_dir"], exist_ok=True)

        # Resolved before the file is written so the local file and the S3 object share a name.
        key = None
        if no_upload:
            filename = self._unique_filename(options["output_dir"], stem, extension)
        else:
            key = self._unique_key(table, stem, extension)
            filename = os.path.basename(key)

        file_path = os.path.join(options["output_dir"], filename)

        pks = self._write_backup(
            table, file_path, where_sql, where_params, datetime_field, delete, compress
        )
        written = len(pks) if delete else record_count
        self.stdout.write(
            f"Wrote {written} record(s) to {file_path} "
            f"({os.path.getsize(file_path) / 1024:,.1f} KiB)"
        )

        uploaded = False
        if key is not None:
            self.stdout.write(f"Uploading to s3://{settings.AWS_BACKUP_BUCKET}/{key}")
            content_type = GZIP_CONTENT_TYPE if compress else CONTENT_TYPE
            s3.upload_file(settings.AWS_BACKUP_BUCKET, file_path, key, content_type=content_type)
            self._verify_upload(key, file_path)
            uploaded = True
            self.stdout.write("Upload complete")

        if delete:
            deleted = self._delete_records(table, pks, where_sql, where_params)
            self.stdout.write(f"Deleted {deleted} record(s) from {table}")
            skipped = len(pks) - deleted
            if skipped > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f"{skipped} backed up record(s) no longer match the filter and were left "
                        f"in {table}; they are still in the backup file"
                    )
                )

        if uploaded and not options["keep_local"]:
            os.remove(file_path)

        self.stdout.write(self.style.SUCCESS(f"{table} backup complete"))

    def _report_dry_run(self, table, record_count, stem, extension, output_dir, no_upload, delete):
        """Report what a real run would do. No file is written and nothing in S3 is touched, so
        the destination is the unsuffixed name -- a run that finds it taken picks a '_N' variant
        of it instead."""
        destination = os.path.join(output_dir, f"{stem}{extension}")
        if not no_upload:
            destination = (
                f"s3://{settings.AWS_BACKUP_BUCKET}/{self._s3_key(table, f'{stem}{extension}')}"
            )
        self.stdout.write(f"Dry run: would back up {record_count} record(s) to {destination}")
        if delete:
            self.stdout.write(
                f"Dry run: would then delete those {record_count} record(s) from {table}"
            )
        self.stdout.write("Dry run: nothing was written, uploaded or deleted")

    def _confirm_delete(self, table, datetime_field, record_count, min_value, max_value):
        """Ask before a run that permanently removes records. Deleted records cannot be recovered
        from the application side, so a run that cannot prompt has to say so with --noinput
        rather than have the answer assumed for it."""
        if not sys.stdin or not sys.stdin.isatty():
            raise CommandError(
                "--delete needs confirmation, but there is no terminal to prompt on. Re-run with "
                "--noinput to confirm up front, or with --dry-run to see what would be deleted."
            )

        self.stdout.write(
            self.style.WARNING(
                f"--delete will permanently remove {record_count} record(s) from {table} with "
                f"{datetime_field} from {min_value} to {max_value} once they have been backed up "
                "and the upload has been verified. This cannot be undone."
            )
        )
        if input("Type 'yes' to continue, or anything else to cancel: ") != "yes":
            raise CommandError("Cancelled; nothing has been backed up or deleted")

    def _verify_upload(self, key, file_path):
        """Confirm the uploaded object is the backup that was just written before anything is
        deleted on the strength of it.

        The object existing at the key is not enough on its own: a concurrent run could have put
        a different object there, or the transfer could have produced a short one. Comparing
        sizes catches both. upload_file sends the file as-is (no ContentEncoding is set, so S3
        does not transform the body), which makes the local size the size to expect.
        """
        head = s3.head_object(settings.AWS_BACKUP_BUCKET, key)
        if head is None:
            raise CommandError(
                f"Upload of {key} could not be verified; no records have been deleted"
            )

        local_size = os.path.getsize(file_path)
        uploaded_size = head.get("ContentLength")
        if uploaded_size != local_size:
            raise CommandError(
                f"Uploaded object {key} is {uploaded_size} byte(s) but the backup file written "
                f"locally is {local_size} byte(s), so it is not the file that was just uploaded; "
                "no records have been deleted"
            )

    def _make_aware(self, value):
        if value is None or timezone.is_aware(value):
            return value
        return timezone.make_aware(value)

    def _validate_table(self, table):
        """Confirm the table exists in a schema on the search path."""
        with connection.cursor() as cursor:
            cursor.execute("SELECT to_regclass(%s)", [quote_identifier(table)])
            if cursor.fetchone()[0] is None:
                raise CommandError(f"Table '{table}' does not exist")

    def _validate_datetime_field(self, table, field):
        quote_identifier(field)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT format_type(a.atttypid, a.atttypmod)
                FROM pg_attribute a
                WHERE a.attrelid = to_regclass(%s)
                    AND a.attname = %s
                    AND a.attnum > 0
                    AND NOT a.attisdropped
                """,
                [quote_identifier(table), field],
            )
            row = cursor.fetchone()

        if row is None:
            raise CommandError(f"Table '{table}' has no column '{field}'")

        if not is_datetime_type(row[0]):
            raise CommandError(
                f"Column '{field}' on '{table}' is of type '{row[0]}', not a date/datetime type"
            )

    def _get_pk_column(self, table):
        """Return the name of the table's single-column primary key."""
        if self._pk_column is not None:
            return self._pk_column

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT a.attname
                FROM pg_index i
                JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                WHERE i.indrelid = to_regclass(%s) AND i.indisprimary
                """,
                [quote_identifier(table)],
            )
            columns = [r[0] for r in cursor.fetchall()]

        if not columns:
            raise CommandError(f"Table '{table}' has no primary key, so --delete cannot be used")
        if len(columns) > 1:
            raise CommandError(
                f"Table '{table}' has a composite primary key ({', '.join(columns)}), "
                "so --delete cannot be used"
            )
        self._pk_column = columns[0]
        return self._pk_column

    def _build_where(self, datetime_field, start_date, end_date):
        quoted_field = quote_identifier(datetime_field)
        clauses = [f"t.{quoted_field} < %s"]
        params = [end_date]
        if start_date:
            clauses.append(f"t.{quoted_field} >= %s")
            params.append(start_date)
        # Rows with a NULL datetime field have no age to judge, so they are never backed up.
        clauses.append(f"t.{quoted_field} IS NOT NULL")
        return " AND ".join(clauses), params

    def _summarize(self, table, datetime_field, where_sql, where_params):
        quoted_table = quote_identifier(table)
        quoted_field = quote_identifier(datetime_field)
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT COUNT(*), MIN(t.{quoted_field}), MAX(t.{quoted_field}) "
                f"FROM {quoted_table} t WHERE {where_sql}",
                where_params,
            )
            return cursor.fetchone()

    def _build_stem(self, table, start_value, end_value):
        start = start_value.strftime("%Y%m%d")
        end = end_value.strftime("%Y%m%d")
        return f"{table}_{start}_{end}"

    def _build_extension(self, compress):
        if compress:
            return f".{BACKUP_EXTENSION}.{GZIP_EXTENSION}"
        return f".{BACKUP_EXTENSION}"

    def _s3_key(self, table, filename):
        return f"{RECORDS_DIR}/{table}/{filename}"

    def _unique_key(self, table, stem, extension):
        """Return an S3 key for stem + extension that is not already in the bucket.

        S3 overwrites an existing object silently, which would discard an earlier backup covering
        the same date range, so a taken key gets an incrementing '_N' suffix instead. The suffix
        goes on the stem so the extensions stay at the end of the name.
        """
        key = self._s3_key(table, f"{stem}{extension}")
        if not s3.file_exists(settings.AWS_BACKUP_BUCKET, key):
            return key

        for n in range(1, MAX_FILENAME_SUFFIX + 1):
            candidate = self._s3_key(table, f"{stem}_{n}{extension}")
            if not s3.file_exists(settings.AWS_BACKUP_BUCKET, candidate):
                self.stdout.write(f"{key} already exists; backing up to {candidate} instead")
                return candidate

        raise CommandError(
            f"{key} already exists, as do the first {MAX_FILENAME_SUFFIX} suffixed variants of it"
        )

    def _unique_filename(self, output_dir, stem, extension):
        """Return a filename for stem + extension that is not already taken in output_dir.

        Writing the file would truncate an earlier backup covering the same date range, so a taken
        name gets an incrementing '_N' suffix, the same way S3 keys are made unique.
        """
        filename = f"{stem}{extension}"
        if not os.path.exists(os.path.join(output_dir, filename)):
            return filename

        for n in range(1, MAX_FILENAME_SUFFIX + 1):
            candidate = f"{stem}_{n}{extension}"
            if not os.path.exists(os.path.join(output_dir, candidate)):
                self.stdout.write(f"{filename} already exists; backing up to {candidate} instead")
                return candidate

        raise CommandError(
            f"{filename} already exists, as do the first {MAX_FILENAME_SUFFIX} suffixed variants "
            "of it"
        )

    def _open_backup_file(self, file_path, compress):
        """Compression happens a line at a time as the records stream past, so memory stays flat
        no matter how large the backup is."""
        if compress:
            return gzip.open(
                file_path, mode="wt", encoding="utf-8", compresslevel=GZIP_COMPRESS_LEVEL
            )
        return open(file_path, "w", encoding="utf-8")

    def _write_backup(
        self, table, file_path, where_sql, where_params, datetime_field, collect_pks, compress
    ):
        """Stream matching records to file_path, one JSON object per line, gzipped when compress
        is set. Returns the list of primary keys written when collect_pks is set (for a later
        delete), otherwise an empty list. A failure part way through removes the partial file
        before re-raising.

        Postgres does the JSON encoding via to_jsonb, so every column type the database can
        output -- including PostGIS geometry and jsonb -- is serialized without needing a
        Python-side encoder.
        """
        quoted_table = quote_identifier(table)
        quoted_field = quote_identifier(datetime_field)
        pk_column = self._get_pk_column(table) if collect_pks else None

        select_columns = "to_jsonb(t)::text"
        if pk_column:
            select_columns = f"t.{quote_identifier(pk_column)}, {select_columns}"

        sql = (
            f"SELECT {select_columns} FROM {quoted_table} t "
            f"WHERE {where_sql} ORDER BY t.{quoted_field}"
        )

        pks = []
        try:
            # A server-side cursor keeps memory flat regardless of how many records match.
            with connection.chunked_cursor() as cursor:
                cursor.execute(sql, where_params)
                with self._open_backup_file(file_path, compress) as f:
                    for row in cursor:
                        if pk_column:
                            pks.append(row[0])
                            f.write(row[1])
                        else:
                            f.write(row[0])
                        f.write("\n")
        except BaseException:
            # A half-written file is not a backup. Left behind it would take up room in an output
            # directory that is often shared or short-lived, read as a valid backup to anyone
            # looking at the directory later, and push the next attempt onto a '_N' suffixed name.
            with contextlib.suppress(OSError):
                os.remove(file_path)
            raise
        return pks

    def _delete_records(self, table, pks, where_sql, where_params):
        """Delete the records that were backed up, by primary key, so records added between the
        backup and the delete are never caught up in it.

        The datetime filter is re-applied to the delete as well: minutes can pass between reading
        a record and deleting it (the upload and its verification happen in between), and in that
        window a record's datetime field can be updated to a value outside the range that was
        backed up. Such a record no longer matches the filter, so it is left in place rather than
        deleted on the strength of a backup of its earlier state.

        Each batch is committed on its own. Holding every batch open in one transaction would
        keep row locks for the whole delete and hold back the vacuum horizon for other tables,
        which is what batching is meant to avoid. The cost is that a failure part way through
        leaves some of the backed up records deleted and the rest in place; the run is safe to
        repeat, since deleting an already deleted primary key does nothing.
        """
        quoted_table = quote_identifier(table)
        pk_column = quote_identifier(self._get_pk_column(table))
        deleted = 0
        try:
            with connection.cursor() as cursor:
                for offset in range(0, len(pks), DELETE_BATCH_SIZE):
                    batch = pks[offset : offset + DELETE_BATCH_SIZE]
                    placeholders = ", ".join(["%s"] * len(batch))
                    with transaction.atomic():
                        cursor.execute(
                            f"DELETE FROM {quoted_table} t "
                            f"WHERE t.{pk_column} IN ({placeholders}) AND {where_sql}",
                            batch + list(where_params),
                        )
                        deleted += cursor.rowcount
        except Exception:
            self.stdout.write(
                self.style.WARNING(
                    f"Delete failed after {deleted} of {len(pks)} record(s) were deleted from "
                    f"{table}; the backup file covers all of them, and re-running the delete for "
                    "the remainder is safe"
                )
            )
            raise
        return deleted
