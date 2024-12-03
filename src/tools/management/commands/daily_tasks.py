from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = """
    Used for running daily tasks like database backup and metrics update.
    """

    def handle(self, **options):
        try:
            call_command("dbbackup")
        except Exception as e:
            self.stderr.write(f"Database backup error: {str(e)}")

        try:
            # Update metrics for the previous day (UTC)
            call_command("update_metrics")
        except Exception as e:
            self.stderr.write(f"Update metrics error: {str(e)}")
