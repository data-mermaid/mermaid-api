from django.conf import settings
from django.core.management.base import BaseCommand

from api.models import CollectRecord, Image, ObsBenthicPhotoQuadrat, Project
from api.utils.image_migration import migrate_project_images


class Command(BaseCommand):
    help = (
        "Check for images whose image_bucket doesn't match the expected bucket based on "
        "project status, and optionally fix them.\n\n"
        "Test-project images should be in the test bucket; all other images should be in the "
        "production bucket. Reports inconsistencies and, without --dry-run, corrects them."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report inconsistencies without making any changes.",
        )
        parser.add_argument(
            "--skip-delete",
            action="store_true",
            help="When fixing, copy S3 files without deleting from the source bucket.",
        )

    def _get_test_image_ids(self, test_project_ids):
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

        return cr_image_ids | obs_image_ids

    def _print_sample(self, queryset, expected_bucket, limit=20):
        sample = queryset[:limit].values_list("id", "name", "image_bucket")
        for img_id, name, bucket in sample:
            current = bucket or "(empty)"
            self.stdout.write(f"  {img_id}  {name}  {current} -> {expected_bucket}")
        total = queryset.count()
        if total > limit:
            self.stdout.write(f"  ... and {total - limit} more")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
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
            self.stdout.write("(Buckets are the same — no S3 moves needed)")
        self.stdout.write("")

        # --- Discover test images ---

        test_project_ids = set(
            Project.objects.filter(status=Project.TEST).values_list("id", flat=True)
        )
        test_image_ids = self._get_test_image_ids(test_project_ids)

        self.stdout.write(f"Test projects: {len(test_project_ids)}")
        self.stdout.write(f"Test-project images: {len(test_image_ids)}")

        # --- Find misplaced images ---

        misplaced_test = (
            Image.objects.filter(id__in=test_image_ids).exclude(image_bucket=test_bucket)
            if test_image_ids
            else Image.objects.none()
        )
        misplaced_non_test = (
            Image.objects.exclude(id__in=test_image_ids).exclude(image_bucket=prod_bucket)
            if test_image_ids
            else Image.objects.exclude(image_bucket=prod_bucket)
        )

        misplaced_test_count = misplaced_test.count()
        misplaced_non_test_count = misplaced_non_test.count()

        self.stdout.write(
            f"Misplaced test images (should be in {test_bucket}): {misplaced_test_count}"
        )
        self.stdout.write(
            f"Misplaced non-test images (should be in {prod_bucket}): {misplaced_non_test_count}"
        )

        if misplaced_test_count == 0 and misplaced_non_test_count == 0:
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("All images are in the correct bucket."))
            return

        # --- Show samples ---

        if misplaced_test_count > 0:
            self.stdout.write("")
            self.stdout.write("Sample misplaced test images:")
            self._print_sample(misplaced_test, test_bucket)

        if misplaced_non_test_count > 0:
            self.stdout.write("")
            self.stdout.write("Sample misplaced non-test images:")
            self._print_sample(misplaced_non_test, prod_bucket)

        if dry_run:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("DRY RUN — no changes made."))
            return

        # --- Fix non-test images (DB only — files are already in prod bucket) ---

        if misplaced_non_test_count > 0:
            self.stdout.write("")
            updated = misplaced_non_test.update(image_bucket=prod_bucket)
            self.stdout.write(f"Fixed {updated} non-test images -> {prod_bucket} (DB only)")

        # --- Fix test images ---

        if misplaced_test_count > 0:
            self.stdout.write("")
            if buckets_differ:
                total_moved = 0
                test_projects = Project.objects.filter(id__in=test_project_ids)
                for i, project in enumerate(test_projects.iterator(), 1):
                    self.stdout.write(
                        f"  [{i}/{len(test_project_ids)}] {project.name} ({project.pk})"
                    )
                    count = migrate_project_images(
                        project.pk,
                        prod_bucket,
                        test_bucket,
                        skip_delete=skip_delete,
                    )
                    self.stdout.write(f"    moved {count} images")
                    total_moved += count
                self.stdout.write(f"Fixed {total_moved} test images -> {test_bucket} (S3 + DB)")
            else:
                updated = (
                    Image.objects.filter(id__in=test_image_ids)
                    .exclude(image_bucket=test_bucket)
                    .update(image_bucket=test_bucket)
                )
                self.stdout.write(
                    f"Fixed {updated} test images -> {test_bucket} (DB only, same bucket)"
                )

        self.stdout.write(self.style.SUCCESS("Done."))
