import csv
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
        # TODO: save to S3?
