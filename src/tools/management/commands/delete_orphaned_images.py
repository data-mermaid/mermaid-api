from django.core.management.base import BaseCommand
from django.db.models import Exists, OuterRef, Q

from api.models import CollectRecord, Image, ObsBenthicPhotoQuadrat


class Command(BaseCommand):
    help = "Deletes orphaned Images (no matching CollectRecord and not referenced by ObsBenthicPhotoQuadrat)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only show which images would be deleted, without actually deleting.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        self.stdout.write("Finding orphaned images...")

        valid_collect_ids = CollectRecord.objects.values_list("id", flat=True)
        orphaned_images = (
            Image.objects.filter(~Q(collect_record_id__in=valid_collect_ids))
            .annotate(is_used=Exists(ObsBenthicPhotoQuadrat.objects.filter(image=OuterRef("pk"))))
            .filter(is_used=False)
        )

        count = orphaned_images.count()

        if count == 0:
            self.stdout.write("No orphaned images found.")
            return

        if dry_run:
            self.stdout.write(f"Dry run: {count} orphaned images would be deleted:")
            for image in orphaned_images:
                self.stdout.write(f"- Image ID: {image.id}, name: {image.name or 'Unnamed'}")
        else:
            self.stdout.write(f"Deleting {count} orphaned images...")
            for image in orphaned_images:
                self.stdout.write(
                    f"- Deleting image ID: {image.id}, name: {image.name or 'Unnamed'}"
                )
                # file cleanup happens via signal
                image.delete()

            self.stdout.write("Orphaned images cleanup completed.")
