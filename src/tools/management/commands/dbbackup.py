import os
import shlex

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from simpleflake import simpleflake

from api.utils import run_subprocess, s3

BACKUP_EXTENSION = "dump"

# "local" backups are a shared, hand-curated dataset devs restore from instead of prod —
# not a rotating series, so they're exempt from age-based cleanup.
CLEANUP_EXEMPT_BACKUP_NAME = "local"


class Command(BaseCommand):
    help = "Dump the database and upload the backup to S3"

    def __init__(self):
        super(Command, self).__init__()
        self.now = timezone.now()
        self.env = os.environ.get("ENV", "none").lower()
        self.backup = self.env
        self.local_file_location = os.path.join(os.path.sep, "tmp", "mermaid")
        os.makedirs(self.local_file_location, exist_ok=True)

    def add_arguments(self, parser):
        parser.add_argument("backup", nargs="?", type=str)
        parser.add_argument(
            "-n",
            action="store_true",
            dest="no_upload",
            default=False,
            help="Do not upload dumped data to S3",
        )
        parser.add_argument(
            "--cron",
            "-c",
            action="store_true",
            default=False,
            help="Execute within a scheduled context only appropriate for production environment",
        )

    def handle(self, *args, **options):
        if options.get("cron") and self.env != "prod":
            self.stdout.write("Skipping backup in cron context not in production")
            return None

        backup_name = options.get("backup")
        if backup_name:
            if not isinstance(backup_name, str):
                self.stdout.write(self.style.ERROR("Incorrect argument type"))
                return None
            self.backup = backup_name

        self.stdout.write(f"ENV: {self.env}")
        self.stdout.write(f"BACKUP: {self.backup}")

        backup_id = simpleflake()
        new_aws_key_name = f"{self.backup}/mermaid_backup_{backup_id}.{BACKUP_EXTENSION}"
        new_backup_filename = f"{self.backup}_mermaid_backup_{backup_id}.{BACKUP_EXTENSION}"
        new_backup_path = os.path.join(self.local_file_location, new_backup_filename)

        self.pg_dump(new_backup_path)

        if not options.get("no_upload"):
            self.stdout.write(
                f"Uploading {new_aws_key_name} to S3 bucket {settings.AWS_BACKUP_BUCKET}"
            )
            s3.upload_file(settings.AWS_BACKUP_BUCKET, new_backup_path, new_aws_key_name)
            self.stdout.write("Upload complete")

        if self.backup == CLEANUP_EXEMPT_BACKUP_NAME:
            self.stdout.write(
                f"Skipping cleanup for '{self.backup}' (exempt from age-based cleanup)"
            )
        else:
            # The backup itself has already succeeded by this point, so a cleanup failure
            # (throttling, network blip) is logged, not raised — it must not surface as a
            # false "backup failed" alert (see daily_tasks.py's call_command wrapper).
            try:
                self._cleanup_stale_backups()
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f"Cleanup failed (backup itself succeeded): {e}")
                )

        self.stdout.write(self.style.SUCCESS("Backup complete"))

    def _cleanup_stale_backups(self):
        client = s3.get_client()
        bucket_file_list = s3.list_objects(settings.AWS_BACKUP_BUCKET, prefix=f"{self.backup}/")
        if bucket_file_list:
            for s3_obj in bucket_file_list:
                age = (self.now - s3_obj["LastModified"]).days
                if age > settings.S3_DBBACKUP_MAXAGE:
                    s3.delete_file(settings.AWS_BACKUP_BUCKET, s3_obj["Key"], client=client)
                    self.stdout.write(f"{s3_obj['Key']} deleted")
            self.stdout.write("Cleanup complete")

    def pg_dump(self, filename):
        params = {
            "db_user": settings.DATABASES["default"]["USER"],
            "db_host": settings.DATABASES["default"]["HOST"],
            "db_name": settings.DATABASES["default"]["NAME"],
            "dump_file": filename,
        }

        dump_command_str = "pg_dump -F c -v -U {db_user} -h {db_host} -d {db_name} -f {dump_file}"
        dump_command = shlex.split(dump_command_str.format(**params))
        run_subprocess(dump_command, to_file="/tmp/mermaid/std_out_backup.log")
        self.stdout.write("Dump complete")
