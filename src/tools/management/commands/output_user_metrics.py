import csv

import boto3
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from tools.metrics import agg_log_events
from tools.models import LogEvent


class Command(BaseCommand):
    def handle(self, *args, **options):
        les = LogEvent.objects.all()
        agg_les = agg_log_events(les)
        fieldnames = agg_les[0].keys()
        today = timezone.now().date().isoformat()
        filename = f"user_metrics-{today}.csv"
        with open(filename, "w") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(agg_les)

        session = boto3.session.Session(
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )
        s3 = session.client("s3")
        s3.upload_file(filename, settings.AWS_METRICS_BUCKET, filename)
