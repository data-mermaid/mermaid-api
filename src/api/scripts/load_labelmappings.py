import csv
from pathlib import Path

from api.models import LabelMapping


def run(*args: str) -> None:
    """Load label mappings from a CSV file into the database.

    Args:
        args: Command-line arguments. Expected format:
            args[0]: Path to the CSV file
            args[1]: Provider value that must exist in LabelMapping.PROVIDERS

    Returns:
        None
    """
    if len(args) < 2:
        print("Usage: runscript load_labelmappings --script-args <csv_path> <provider_value>")
        return

    csv_path = Path(args[0])
    provider = args[1]

    if not csv_path.exists():
        print(f"CSV file not found at {csv_path}")
        return

    if provider not in dict(LabelMapping.PROVIDERS):
        print(
            f"Invalid provider value '{provider}'. Must be one of {list(dict(LabelMapping.PROVIDERS).keys())}."
        )
        return

    with open(csv_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            provider_id = row.get("provider id", "").strip()
            provider_label = row.get("provider label", "").strip()
            benthic_attribute_id = row.get("benthic_attribute_id", "").strip()
            growth_form_id = row.get("growth_form_id", "").strip()
            if provider_id == "" or provider_label == "" or benthic_attribute_id == "":
                print(
                    f"Missing data: provider_id {provider_id} provider_label {provider_label} benthic_attribute_id {benthic_attribute_id}"
                )
            if growth_form_id == "":
                growth_form_id = None

            label_mapping, created = LabelMapping.objects.update_or_create(
                provider=provider,
                provider_id=provider_id,
                provider_label=provider_label,
                benthic_attribute_id=benthic_attribute_id,
                growth_form_id=growth_form_id,
            )

            if created:
                print(f"Created LabelMapping: {label_mapping}")
            else:
                print(f"Updated LabelMapping: {label_mapping}")
