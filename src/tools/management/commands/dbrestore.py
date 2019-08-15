import os
import shlex
import subprocess
import traceback
import zipfile
from django.core.management.base import BaseCommand
from django.conf import settings
import boto3
from boto3.s3.transfer import S3Transfer
from optparse import make_option

AWS_ACCESS_KEY_ID = settings.AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY = settings.AWS_SECRET_ACCESS_KEY
AWS_REGION = settings.AWS_REGION
AWS_BACKUP_BUCKET = settings.AWS_BACKUP_BUCKET


class Command(BaseCommand):
    help = "Kill local processes running runserver command"
    requires_system_checks = False

    def __init__(self):
        super(Command, self).__init__()
        self.restore = os.environ.get("RESTORE", "false").lower()
        self.env = os.environ.get("ENV", "none").lower()
        print("ENV: %s" % self.env)
        print("RESTORE: %s" % self.restore)
        self.local_file_location = os.path.join(os.path.sep, "tmp", "mermaid")
        try:
            os.mkdir(self.local_file_location)
        except OSError:
            pass  # Means it already exists.
        session = boto3.session.Session(
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION,
        )
        self.s3 = session.client("s3")

    def get_s3_bucket_obj_list(self, bucket_name):
        try:
            return self.s3.list_objects(Bucket=bucket_name).get("Contents")
        except:
            traceback.print_exc()
            return []

    def add_arguments(self, parser):
        parser.add_argument("restore", nargs="?", type=str)
        parser.add_argument(
            "-f", action="store_true", dest="force", default=False, help="Force restore"
        ),
        parser.add_argument(
            "-n",
            action="store_true",
            dest="no_download",
            default=False,
            help="Do not download dumped " "data from S3",
        )

    def handle(self, *args, **options):
        # Override backup with command line arg value
        restore_name = options.get("restore")
        if restore_name:
            if not isinstance(restore_name, str):
                print("Incorrect argument type")
                return None
            self.restore = restore_name

        if self.restore in ["False", "false"]:
            print("Skipping Restore")
            return None

        if self.env == "prod" and options.get("force") is not True:
            raise Exception("Restoring production database needs to be forced.")

        if options.get("no_download", False) is True:
            download_file_name = None
            tmpdir = os.path.join(os.path.sep, self.local_file_location)

            for f in os.listdir(tmpdir):
                localfile = os.path.join(tmpdir, f)
                if os.path.isfile(localfile) and self.restore in localfile:
                    if download_file_name is None or os.path.getmtime(
                        localfile
                    ) > os.path.getmtime(download_file_name):
                        download_file_name = localfile

            if download_file_name is None:
                raise ValueError("No local files for {} found".format(self.env))
            print(download_file_name)

        else:
            bucket_file_list = self.get_s3_bucket_obj_list(AWS_BACKUP_BUCKET)

            if bucket_file_list and len(bucket_file_list) > 0:
                latest_key_name = None

                # Get key with oldest timestamp, use self.restore to identify which backup
                print("Retrieving latest backup")
                for s3_obj in bucket_file_list:
                    if self.restore in s3_obj["Key"]:
                        if latest_key_name is None:
                            latest_key_name = s3_obj
                            print("Latest Key Name: %s" % latest_key_name["Key"])
                        elif s3_obj.get("LastModified") > latest_key_name.get(
                            "LastModified"
                        ):
                            latest_key_name = s3_obj
                            print("Latest Key Name: %s" % latest_key_name["Key"])

                if latest_key_name is None:
                    raise ValueError("File not found")

                # create download file name
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
                        AWS_BACKUP_BUCKET,
                        latest_key_name.get("Key"),
                        download_file_name,
                    )

                    if not os.path.isfile(download_file_name):
                        raise ValueError("File did not download")

                    # if download_file_name.endswith('zip'):
                    #     print('Extracting...')
                    #     zip = zipfile.ZipFile(download_file_name)
                    #     zip.extractall(self.local_file_location)
                    # TODO extract compressed file before restoring

            else:
                raise ValueError("File not found")

        try:
            self._init_db()
            self._psql_restore_db(download_file_name)
            print("Restore Complete")
        except Exception as e:
            print(traceback.print_exc())
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
            "DROP DATABASE {db_name};",
            "CREATE DATABASE {db_name} OWNER {db_user};",
            "ALTER PROCEDURAL LANGUAGE plpgsql OWNER TO {db_user};",
        ]

        cmd = "psql -a -h {db_host} -d postgres -U {db_user}".format(**params)
        for q in init_db_commands:
            query = "-c '%s'" % q
            psql_command = "%s %s" % (cmd, query.format(**params))
            print(psql_command)
            command = shlex.split(psql_command)
            self._run(command)

        print("Init Complete!")

    def _psql_restore_db(self, file_name):

        params = {
            "sql_loc": file_name,
            "db_user": settings.DATABASES["default"]["USER"],
            "db_host": settings.DATABASES["default"]["HOST"],
            "db_name": settings.DATABASES["default"]["NAME"],
        }

        cmd_str = "psql -U {db_user} -h {db_host} -d {db_name} -q -f {sql_loc}".format(
            **params
        )
        print("$> %s" % cmd_str)

        command = shlex.split(cmd_str)

        self._run(command, to_file="/tmp/mermaid/stdout.log")

    def _run(self, command, std_input=None, to_file=None):
        try:
            proc = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except Exception as e:
            print(command)
            raise e

        data, err = proc.communicate(input=std_input)

        if to_file is not None:
            with open(to_file, "w") as f:
                f.write("DATA: \n")
                f.write(str(data))
                f.write("ERR: \n")
                f.write(str(err))
        else:
            print(data)
            print(err)
