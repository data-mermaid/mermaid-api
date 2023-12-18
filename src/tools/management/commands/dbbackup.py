import os
import shlex
from datetime import datetime, timezone

import boto3
from django.conf import settings
from django.core.management.base import BaseCommand
from simpleflake import simpleflake

from api.utils import run_subprocess

BACKUP_EXTENSION = "sql"


class Command(BaseCommand):
    help = "Kill local processes running runserver command"

    def __init__(self):
        super(Command, self).__init__()
        self.now = datetime.now(timezone.utc)
        self.env = os.environ.get("ENV", "none").lower()
        self.backup = self.env
        self.local_file_location = os.path.join(os.path.sep, "tmp", "mermaid")
        try:
            os.mkdir(self.local_file_location)
        except OSError:
            pass  # Means it already exists.
        session = boto3.session.Session(
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )
        self.s3 = session.client("s3")

    def get_s3_bucket_obj_list(self):
        try:
            return self.s3.list_objects_v2(Bucket=settings.AWS_BACKUP_BUCKET).get("Contents")
        except Exception as e:
            print(e)
            return []

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
            print("Skipping backup in cron context not in production")
            return None

        backup_name = options.get("backup")
        if backup_name:
            if not isinstance(backup_name, str):
                print("Incorrect argument type")
                return None
            self.backup = backup_name

        print(f"ENV: {self.env}")
        print(f"BACKUP: {self.backup}")

        new_aws_key_name = f"{self.backup}/mermaid_backup_{simpleflake()}.{BACKUP_EXTENSION}"
        new_backup_filename = f"{self.backup}_mermaid_backup_{simpleflake()}.{BACKUP_EXTENSION}"
        new_backup_path = os.path.join(self.local_file_location, new_backup_filename)

        self.pg_dump(new_backup_path)

        if not options.get("no_upload"):
            print(f"Uploading {new_aws_key_name} to S3 bucket {settings.AWS_BACKUP_BUCKET}")
            self.s3.upload_file(new_backup_path, settings.AWS_BACKUP_BUCKET, new_aws_key_name)
            print("Upload complete")

        bucket_file_list = self.get_s3_bucket_obj_list()
        if bucket_file_list:
            for s3_obj in bucket_file_list:
                if self.backup in s3_obj["Key"]:
                    age = (self.now - s3_obj.get("LastModified")).days
                    if age > settings.S3_DBBACKUP_MAXAGE:
                        self.s3.delete_object(Bucket=settings.AWS_BACKUP_BUCKET, Key=s3_obj["Key"])
                        print(f"{s3_obj['Key']} deleted")
            print("Cleanup complete")

        print("Backup complete")

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
        print("Dump complete")
