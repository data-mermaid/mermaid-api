from django.core.management import call_command
from django.core.management.base import BaseCommand

call_command("my_command", "foo", bar="baz")


class Command(BaseCommand):
    help = """
    Used for running daily tasks like database backup and metrics update.
    """

    def handle(self, **options):
        call_command("dbbackup")
        call_command("update_metrics")
