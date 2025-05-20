from django.core.management.base import BaseCommand

from api.utils.classification import export_annotations_parquet


class Command(BaseCommand):
    help = "Exports confirmed image annotations to a Parquet file and uploads it to S3."

    def add_arguments(self, parser):
        parser.add_argument("--chunk_size", type=int, default=10000)

    def handle(self, *args, **options):
        chunk_size = options["chunk_size"]

        self.stdout.write(
            f"Starting export of annotations to parquet with chunk size: {chunk_size}"
        )
        try:
            export_annotations_parquet(chunk_size=chunk_size)
            self.stdout.write(self.style.SUCCESS("Export completed successfully."))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Export failed: {e}"))
            raise SystemExit(1)
