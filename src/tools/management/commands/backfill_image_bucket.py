from django.conf import settings
from django.core.management.base import BaseCommand

from api.models import CollectRecord, Image, ObsBenthicPhotoQuadrat, Project
from api.utils.image_migration import migrate_project_images


class Command(BaseCommand):
    help = (
        "Backfill image_bucket on existing Image records and optionally move S3 files "
        "for test-project images to the test bucket.\n\n"
        "Two phases:\n"
        "  1. Set image_bucket on all non-test images to the production bucket (DB only).\n"
        "  2. For test-project images, move S3 files to the test bucket and set image_bucket.\n\n"
        "Use --dry-run to preview. Use --db-only to skip S3 file moves."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would happen without making any changes.",
        )
        parser.add_argument(
            "--db-only",
            action="store_true",
            help="Only update image_bucket in the database; do not move S3 files.",
        )
        parser.add_argument(
            "--skip-delete",
            action="store_true",
            help="Copy files to the test bucket without deleting from the production bucket.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        db_only = options["db_only"]
        skip_delete = options["skip_delete"]

        prod_bucket = settings.IMAGE_PROCESSING_BUCKET or ""
        test_bucket = settings.IMAGE_PROCESSING_BUCKET_TEST or prod_bucket

        if not prod_bucket:
            self.stdout.write(self.style.WARNING("IMAGE_PROCESSING_BUCKET is not set. Aborting."))
            return

        buckets_differ = prod_bucket != test_bucket

        self.stdout.write(f"Production bucket: {prod_bucket}")
        self.stdout.write(f"Test bucket:       {test_bucket}")
        if not buckets_differ:
            self.stdout.write("(Buckets are the same — all images get the same value, no S3 moves)")
        self.stdout.write("")

        # --- Discover images ---

        test_project_ids = set(
            Project.objects.filter(status=Project.TEST).values_list("id", flat=True)
        )

        cr_image_ids = set(
            Image.objects.filter(
                collect_record_id__in=CollectRecord.objects.filter(
                    project_id__in=test_project_ids
                ).values_list("id", flat=True)
            ).values_list("id", flat=True)
        )

        obs_image_ids = set(
            ObsBenthicPhotoQuadrat.objects.filter(
                benthic_photo_quadrat_transect__quadrat_transect__sample_event__site__project_id__in=test_project_ids
            )
            .exclude(image__isnull=True)
            .values_list("image_id", flat=True)
        )

        test_image_ids = cr_image_ids | obs_image_ids
        unset_non_test = Image.objects.filter(image_bucket="").exclude(id__in=test_image_ids)
        unset_test = (
            Image.objects.filter(image_bucket="", id__in=test_image_ids)
            if test_image_ids
            else Image.objects.none()
        )
        already_set = Image.objects.exclude(image_bucket="").count()

        self.stdout.write(f"Test projects: {len(test_project_ids)}")
        self.stdout.write(f"Test-project images (unique): {len(test_image_ids)}")
        self.stdout.write(f"  - found via CollectRecord: {len(cr_image_ids)}")
        self.stdout.write(f"  - found via observation: {len(obs_image_ids)}")
        self.stdout.write(f"Non-test images needing backfill: {unset_non_test.count()}")
        self.stdout.write(f"Test images needing backfill: {unset_test.count()}")
        self.stdout.write(f"Already have image_bucket set: {already_set}")
        self.stdout.write(f"Total images: {Image.objects.count()}")

        needs_s3_move = buckets_differ and not db_only and unset_test.exists()
        if needs_s3_move:
            self.stdout.write("")
            self.stdout.write(
                f"S3 moves: {unset_test.count()} test images " f"({prod_bucket} -> {test_bucket})"
            )
            if skip_delete:
                self.stdout.write("  --skip-delete: source files will NOT be deleted")

        # --- Dry run ---

        if dry_run:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("DRY RUN — no changes made."))

            if test_image_ids:
                self.stdout.write("")
                self.stdout.write("Sample test-project images:")
                sample = Image.objects.filter(id__in=list(test_image_ids)[:20]).values_list(
                    "id", "name", "image_bucket"
                )
                for img_id, name, bucket in sample:
                    current = bucket or "(empty)"
                    self.stdout.write(f"  {img_id}  {name}  {current} -> {test_bucket}")
                if len(test_image_ids) > 20:
                    self.stdout.write(f"  ... and {len(test_image_ids) - 20} more")
            return

        # --- Phase 1: backfill non-test images (DB only) ---

        self.stdout.write("")
        updated_prod = unset_non_test.update(image_bucket=prod_bucket)
        self.stdout.write(
            f"Phase 1: set image_bucket on {updated_prod} non-test images -> {prod_bucket}"
        )

        # --- Phase 2: test images ---

        if not test_image_ids:
            self.stdout.write("Phase 2: no test images to process")
            self.stdout.write(self.style.SUCCESS("Done."))
            return

        if not buckets_differ or db_only:
            # Same bucket or --db-only: just update the field
            updated_test = 0
            if test_image_ids:
                updated_test = Image.objects.filter(id__in=test_image_ids).update(
                    image_bucket=test_bucket
                )
            label = "(DB only, no S3 moves)" if db_only else "(same bucket)"
            self.stdout.write(
                f"Phase 2: set image_bucket on {updated_test} test images -> {test_bucket} {label}"
            )
        else:
            # Different buckets: move S3 files per project, then update image_bucket
            total_moved = 0
            test_projects = Project.objects.filter(id__in=test_project_ids)
            for i, project in enumerate(test_projects.iterator(), 1):
                self.stdout.write(f"  [{i}/{len(test_project_ids)}] {project.name} ({project.pk})")
                count = migrate_project_images(
                    project.pk,
                    prod_bucket,
                    test_bucket,
                    skip_delete=skip_delete,
                )
                self.stdout.write(f"    moved {count} images")
                total_moved += count

            self.stdout.write(f"Phase 2: moved {total_moved} test images -> {test_bucket}")

        self.stdout.write(self.style.SUCCESS("Done."))
