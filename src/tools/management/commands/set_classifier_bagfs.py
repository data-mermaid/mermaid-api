import csv

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from api.models.classification import Classifier
from api.models.protocols.benthic import BenthicAttributeGrowthForm


class Command(BaseCommand):
    help = (
        "Set benthic_attribute_growth_forms on a Classifier from a CSV file. "
        "The CSV must have columns: benthic_attribute_id, growth_form_id (may be blank). "
        "Replaces the existing BA/GF set on the classifier. Creates any missing "
        "BenthicAttributeGrowthForm junction records as needed."
    )

    def add_arguments(self, parser):
        parser.add_argument("classifier_id", help="UUID of the Classifier to update.")
        parser.add_argument("csv_file", help="Path to CSV with BA/GF pairs.")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would change without making any changes.",
        )

    def handle(self, *args, **options):
        classifier_id = options["classifier_id"]
        csv_path = options["csv_file"]
        dry_run = options["dry_run"]

        try:
            classifier = Classifier.objects.get(pk=classifier_id)
        except Classifier.DoesNotExist:
            raise CommandError(f"Classifier {classifier_id} not found.")

        pairs = []
        with open(csv_path, newline="") as f:
            for row in csv.DictReader(f):
                ba_id = row["benthic_attribute_id"].strip()
                gf_id = row["growth_form_id"].strip() or None
                if not ba_id:
                    continue
                pairs.append((ba_id, gf_id))

        self.stdout.write(f"Classifier: {classifier} ({classifier.pk})")
        self.stdout.write(f"CSV rows: {len(pairs)}")

        with transaction.atomic():
            bagfs = []
            created_count = 0
            for ba_id, gf_id in pairs:
                bagf, created = BenthicAttributeGrowthForm.objects.get_or_create(
                    benthic_attribute_id=ba_id, growth_form_id=gf_id
                )
                bagfs.append(bagf)
                if created:
                    created_count += 1
                    self.stdout.write(f"  New BenthicAttributeGrowthForm: ba={ba_id} gf={gf_id}")

            if created_count:
                self.stdout.write(f"New BenthicAttributeGrowthForm records: {created_count}")

            existing = set(classifier.benthic_attribute_growth_forms.values_list("pk", flat=True))
            incoming = {b.pk for b in bagfs}
            to_add = incoming - existing
            to_remove = existing - incoming

            self.stdout.write(f"Currently assigned: {len(existing)}")
            self.stdout.write(f"  To add:    {len(to_add)}")
            self.stdout.write(f"  To remove: {len(to_remove)}")
            self.stdout.write(f"  Unchanged: {len(existing & incoming)}")

            if dry_run:
                transaction.set_rollback(True)
                self.stdout.write(self.style.WARNING("Dry run — no changes made."))
                return

            classifier.benthic_attribute_growth_forms.set(bagfs)
            self.stdout.write(
                self.style.SUCCESS(f"Done. Classifier now has {len(incoming)} BA/GF(s).")
            )
