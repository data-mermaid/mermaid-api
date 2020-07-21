import os
import shlex
import subprocess
import traceback
from datetime import datetime

import boto3
from simpleflake import simpleflake

from django.core.management.base import BaseCommand
from django.conf import settings


AWS_ACCESS_KEY_ID = settings.AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY = settings.AWS_SECRET_ACCESS_KEY
AWS_REGION = settings.AWS_REGION

AWS_BACKUP_BUCKET = settings.AWS_BACKUP_BUCKET
BACKUP_EXTENSION = 'sql'


class Command(BaseCommand):
    help = 'Kill local processes running runserver command'

    def __init__(self):
        super(Command, self).__init__()
        self.backup = os.environ.get('BACKUP', 'false').lower()
        self.env = os.environ.get('ENV', 'none').lower()
        print('ENV: %s' % self.env)
        print('BACKUP: %s' % self.backup)
        self.local_file_location = os.path.join(os.path.sep, 'tmp', 'mermaid')
        try:
            os.mkdir(self.local_file_location)
        except OSError:
            pass  # Means it already exists.
        session = boto3.session.Session(
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION
        )
        self.s3 = session.client('s3')

    def add_arguments(self, parser):
        parser.add_argument('backup', nargs='?', type=str)
        parser.add_argument('-n', action='store_true', dest='no_upload', default=False, help='Do not upload dumped '
                                                                                             'data to S3')

    def handle(self, *args, **options):
        # Override backup with command line arg value
        backup_name = options.get('backup')

        if backup_name:
            if not isinstance(backup_name, str):
                print('Incorrect argument type')
                return None
            self.backup = backup_name

        if self.backup in ["False", "false"]:
            print('Skipping Backup')
            return None

        new_aws_key_name = '%s/mermaid_backup_%s.%s' % (self.backup, simpleflake(), BACKUP_EXTENSION)
        new_backup_filename = '%s_mermaid_backup_%s.%s' % (self.backup, simpleflake(), BACKUP_EXTENSION)
        new_backup_path = os.path.join(self.local_file_location, new_backup_filename)
        self._pg_dump(new_backup_path)

        if options.get('no_upload', False) is False:
            print('Uploading {0} to S3 bucket {1}'.format(new_aws_key_name, AWS_BACKUP_BUCKET))
            self.s3.upload_file(new_backup_path, AWS_BACKUP_BUCKET, new_aws_key_name)
            print('Backup Complete')

    def _pg_dump(self, filename):
        params = {
            'db_user': settings.DATABASES['default']['USER'],
            'db_host': settings.DATABASES['default']['HOST'],
            'db_name': settings.DATABASES['default']['NAME'],
            'dump_file': filename
        }

        dump_command_str = 'pg_dump -F c -v -U {db_user} -h {db_host} -d {db_name} -f {dump_file}'
        dump_command = shlex.split(dump_command_str.format(**params))
        self._run(dump_command, to_file='/tmp/mermaid/std_out_backup.log')
        print('Dump Complete!')

    def _run(self, command, std_input=None, to_file=None):
        if to_file is not None:
            out_handler = open(to_file, 'w')
        else:
            out_handler = subprocess.PIPE

        proc = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=out_handler,
            stderr=out_handler
        )
        data = proc.communicate(input=std_input)[0]

        if to_file is None:
            print(data)
