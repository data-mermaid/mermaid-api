from datetime import datetime, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from tools import metrics
from tools.models import LogEvent, UserMetrics


class Command(BaseCommand):
    help = (
        """Update user metrics for a specified date range or all dates since the first log entry."""
    )

    def add_arguments(self, parser):
        parser.add_argument("--start_date", type=str, help="Start date in YYYY-MM-DD format")
        parser.add_argument("--end_date", type=str, help="End date in YYYY-MM-DD format")
        parser.add_argument(
            "--all", action="store_true", help="Process metrics for all available dates"
        )

    def cast(self, date_str):
        try:
            return timezone.make_aware(
                datetime.strptime(date_str, "%Y-%m-%d"), timezone.get_current_timezone()
            )
        except ValueError:
            raise CommandError(f"Invalid date format for '{date_str}'. Use YYYY-MM-DD.")

    def process_day(self, start_datetime, end_datetime):
        log_events = LogEvent.objects.filter(timestamp__range=(start_datetime, end_datetime))
        print(f"Processing {log_events.count()} log events for {start_datetime.date()}...")
        aggregated_metrics = metrics.agg_log_events(log_events)
        UserMetrics.objects.bulk_create([UserMetrics(**row) for row in aggregated_metrics])
        print(f"{len(aggregated_metrics)} user metrics processed for {start_datetime.date()}.")

    def handle(self, **options):
        if options["all"]:
            first_log = LogEvent.objects.order_by("timestamp").first()
            if not first_log:
                raise CommandError("No log events found to process.")
            start_date = first_log.timestamp.date()
            end_date = timezone.now().date()
            current_date = start_date

            while current_date < end_date:
                start_datetime = timezone.make_aware(
                    datetime(current_date.year, current_date.month, current_date.day, 0, 0, 0),
                    timezone.get_current_timezone(),
                )
                end_datetime = start_datetime + timedelta(days=1)
                self.process_day(start_datetime, end_datetime)
                current_date += timedelta(days=1)
        else:
            start_date_str = options["start_date"]
            end_date_str = options["end_date"]

            if start_date_str and end_date_str:
                start_datetime = self.cast(start_date_str)
                end_datetime = self.cast(end_date_str)

                if not start_datetime or not end_datetime:
                    raise CommandError("Valid start_date and end_date must be provided.")
            else:
                previous_datetime = timezone.now() - timedelta(hours=12)
                start_datetime = timezone.make_aware(
                    datetime(
                        previous_datetime.year,
                        previous_datetime.month,
                        previous_datetime.day,
                        0,
                        0,
                        0,
                    ),
                    timezone.get_current_timezone(),
                )
                end_datetime = start_datetime + timedelta(days=1)

            self.process_day(start_datetime, end_datetime)
