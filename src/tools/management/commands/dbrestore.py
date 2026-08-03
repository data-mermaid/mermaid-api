import os
import shlex

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from api.utils import run_subprocess, s3

BACKUP_EXTENSION = "dump"


class Command(BaseCommand):
    help = "Recreate db and restore data from most recent dump"
    requires_system_checks = False

    def __init__(self):
        self.requires_system_checks = []
        super(Command, self).__init__()
        self.env = os.environ.get("ENV", "none").lower()
        self.restore = self.env
        self.local_file_location = os.path.join(os.path.sep, "tmp", "mermaid")
        os.makedirs(self.local_file_location, exist_ok=True)

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
                self.stdout.write(self.style.ERROR("Incorrect argument type"))
                return None
            self.restore = restore_name
        self.stdout.write("ENV: %s" % self.env)
        self.stdout.write("RESTORE: %s" % self.restore)

        if self.env == "prod" and options.get("force") is not True:
            raise Exception("Restoring production database needs to be forced.")

        try:
            if options.get("no_download", False) is True:
                download_file_name = None
                tmpdir = os.path.join(os.path.sep, self.local_file_location)

                expected_prefix = f"{self.restore}_mermaid_backup_"
                expected_suffix = f".{BACKUP_EXTENSION}"
                for f in os.listdir(tmpdir):
                    localfile = os.path.join(tmpdir, f)
                    if (
                        os.path.isfile(localfile)
                        and f.startswith(expected_prefix)
                        and f.endswith(expected_suffix)
                    ):
                        if download_file_name is None or os.path.getmtime(
                            localfile
                        ) > os.path.getmtime(download_file_name):
                            download_file_name = localfile

                if download_file_name is None:
                    raise ValueError("No local files for {} found".format(self.env))
                self.stdout.write(download_file_name)

            else:
                self.stdout.write("Retrieving latest backup")
                backup_objects = [
                    obj
                    for obj in s3.list_objects(
                        settings.AWS_BACKUP_BUCKET, prefix=f"{self.restore}/"
                    )
                    if not obj["Key"].endswith("/") and obj["Key"].endswith(f".{BACKUP_EXTENSION}")
                ]

                if not backup_objects:
                    raise ValueError(
                        f"{settings.AWS_BACKUP_BUCKET} does not exist or is not listable"
                    )

                latest_obj = max(backup_objects, key=lambda o: o["LastModified"])

                self.stdout.write("Latest Key Name: %s" % latest_obj["Key"])

                download_file_name = os.path.join(
                    os.path.sep,
                    self.local_file_location,
                    "{0}_{1}".format(
                        latest_obj["LastModified"].strftime("%Y%m%d%H%M%S"),
                        latest_obj["Key"].replace("/", "_"),
                    ),
                )

                # If the file doesn't exist locally, then download
                if not os.path.isfile(download_file_name):  # Check if the file exists
                    self.stdout.write(
                        "Downloading: {0} to: {1} ".format(latest_obj["Key"], download_file_name)
                    )

                    s3.download_file(
                        settings.AWS_BACKUP_BUCKET,
                        latest_obj["Key"],
                        download_file_name,
                    )

            if (
                not download_file_name
                or not os.path.isfile(download_file_name)
                or not download_file_name.endswith(f".{BACKUP_EXTENSION}")
            ):
                raise ValueError("No database dump file to restore")
            self._init_db()
            self._psql_restore_db(download_file_name)
            self.stdout.write(self.style.SUCCESS("Restore Complete"))
        except Exception as e:
            raise CommandError(f"Restore FAILED! {e}") from e

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
            "ALTER DATABASE {db_name} SET jit TO false;",
        ]

        cmd = "psql -a -v ON_ERROR_STOP=1 -h {db_host} -d postgres -U {db_user}".format(**params)
        for q in init_db_commands:
            query = "-c '%s'" % q
            psql_command = "%s %s" % (cmd, query.format(**params))
            self.stdout.write(psql_command)
            command = shlex.split(psql_command)
            run_subprocess(command)

        self.stdout.write(self.style.SUCCESS("Init Complete!"))

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
        self.stdout.write("$> %s" % cmd_str)

        command = shlex.split(cmd_str)

        run_subprocess(command, to_file="/tmp/mermaid/std_out_restore.log")
