from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import Classifier


class Command(BaseCommand):
    help = "Ingest a version's model.json from S3 into its Classifier row (config + BA+GF labels)."

    def add_arguments(self, parser):
        parser.add_argument("version", help="Classifier version, e.g. v3")
        parser.add_argument("--name", default=None, help="Optional display name")
        parser.add_argument("--description", default=None, help="Optional description")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate and resolve, then roll back without writing.",
        )

    def handle(self, *args, **options):
        version = options["version"]
        dry_run = options["dry_run"]

        try:
            with transaction.atomic():
                classifier = Classifier.register(
                    version,
                    name=options["name"],
                    description=options["description"],
                )
                label_count = classifier.benthic_attribute_growth_forms.count()
                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(
                            f"[dry-run] would register {version}: config={classifier.config}, "
                            f"{label_count} labels — rolling back."
                        )
                    )
                    transaction.set_rollback(True)
                    return
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to register {version}: {e}"))
            raise

        self.stdout.write(
            self.style.SUCCESS(
                f"Registered {version}: config={classifier.config}, {label_count} labels."
            )
        )
