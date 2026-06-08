import os
import shlex

import boto3
from django.conf import settings
from django.core.management.base import BaseCommand

from api.utils import run_subprocess


class Command(BaseCommand):
    help = "Recreate db and restore data from most recent dump"
    requires_system_checks = False

    def __init__(self):
        self.requires_system_checks = []
        super(Command, self).__init__()
        self.env = os.environ.get("ENV", "none").lower()
        self.restore = self.env
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

    def get_s3_bucket_obj_list(self, bucket_name):
        try:
            return self.s3.list_objects(Bucket=bucket_name).get("Contents")
        except Exception as e:
            print(e)
            return []

    def add_arguments(self, parser):
        parser.add_argument("restore", nargs="?", type=str)
        (
            parser.add_argument(
                "-f", action="store_true", dest="force", default=False, help="Force restore"
            ),
        )
        parser.add_argument(
            "-n",
            action="store_true",
            dest="no_download",
            default=False,
            help="Do not download dumped data from S3",
        )

    def handle(self, *args, **options):
        # Override backup with command line arg value
        restore_name = options.get("restore")
        if restore_name:
            if not isinstance(restore_name, str):
                print("Incorrect argument type")
                return None
            self.restore = restore_name
        print("ENV: %s" % self.env)
        print("RESTORE: %s" % self.restore)

        if self.env == "prod" and options.get("force") is not True:
            raise Exception("Restoring production database needs to be forced.")

        if options.get("no_download", False) is True:
            download_file_name = None
            tmpdir = os.path.join(os.path.sep, self.local_file_location)

            for f in os.listdir(tmpdir):
                localfile = os.path.join(tmpdir, f)
                if os.path.isfile(localfile) and self.restore in localfile:
                    if download_file_name is None or os.path.getmtime(localfile) > os.path.getmtime(
                        download_file_name
                    ):
                        download_file_name = localfile

            if download_file_name is None:
                raise ValueError("No local files for {} found".format(self.env))
            print(download_file_name)

        else:
            bucket_file_list = self.get_s3_bucket_obj_list(settings.AWS_BACKUP_BUCKET)
            download_file_name = ""

            if bucket_file_list:
                latest_key_name = None

                # Get key with oldest timestamp, use self.restore to identify which backup
                print("Retrieving latest backup")
                for s3_obj in bucket_file_list:
                    if self.restore in s3_obj["Key"]:
                        if latest_key_name is None or s3_obj.get(
                            "LastModified"
                        ) > latest_key_name.get("LastModified"):
                            latest_key_name = s3_obj
                            print("Latest Key Name: %s" % latest_key_name["Key"])

                if latest_key_name and latest_key_name["Key"][-1] != "/":
                    download_file_name = os.path.join(
                        os.path.sep,
                        self.local_file_location,
                        "{0}_{1}".format(
                            latest_key_name.get("LastModified").strftime("%Y%m%d%H%M%S"),
                            latest_key_name.get("Key").replace("/", "_"),
                        ),
                    )

                    # If the file doesn't exist locally, then download
                    if not os.path.isfile(download_file_name):  # Check if the file exists
                        print(
                            "Downloading: {0} to: {1} ".format(
                                latest_key_name.get("Key"), download_file_name
                            )
                        )

                        self.s3.download_file(
                            settings.AWS_BACKUP_BUCKET,
                            latest_key_name.get("Key"),
                            download_file_name,
                        )

            else:
                raise ValueError(f"{settings.AWS_BACKUP_BUCKET} does not exist or is not listable")

        try:
            self._init_db()
            if not os.path.isfile(download_file_name):
                raise ValueError("No database dump file to restore")
            self._psql_restore_db(download_file_name)
            print("Restore Complete")
        except Exception as e:
            print(e)
            print("Restore FAILED!")

        # if options.get('no_download', False) is False:
        #     os.remove(download_file_name)

    def _init_db(self):
        params = {
            "db_user": settings.DATABASES["default"]["USER"],
            "db_host": settings.DATABASES["default"]["HOST"],
            "db_name": settings.DATABASES["default"]["NAME"],
        }

        init_db_commands = [
            """SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = $${db_name}$$;""",
            "DROP DATABASE IF EXISTS {db_name};",
            "CREATE DATABASE {db_name} OWNER {db_user};",
            "ALTER PROCEDURAL LANGUAGE plpgsql OWNER TO {db_user};",
            "ALTER DATABASE {db_name} SET jit TO false;",
        ]

        cmd = "psql -a -h {db_host} -d postgres -U {db_user}".format(**params)
        for q in init_db_commands:
            query = "-c '%s'" % q
            psql_command = "%s %s" % (cmd, query.format(**params))
            print(psql_command)
            command = shlex.split(psql_command)
            run_subprocess(command)

        print("Init Complete!")

    def _psql_restore_db(self, file_name):
        params = {
            "sql_loc": file_name,
            "db_user": settings.DATABASES["default"]["USER"],
            "db_host": settings.DATABASES["default"]["HOST"],
            "db_name": settings.DATABASES["default"]["NAME"],
        }

        cmd_str = "pg_restore -O -x -F c --jobs=4 -U {db_user} -h {db_host} -d {db_name} {sql_loc}".format(
            **params
        )
        print("$> %s" % cmd_str)

        command = shlex.split(cmd_str)

        run_subprocess(command, to_file="/tmp/mermaid/std_out_restore.log")
