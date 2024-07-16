import csv
from pathlib import Path

from django.conf import settings
from django.db.utils import IntegrityError

from api.models import BenthicAttribute

"""
Script for importing into one mermaid db a csv exported from the benthic_attribute table in another mermaid db.
[Example: make dev db have same BAs as prod db.]
"""


def _val_or_none(val):
    if val.upper() == "NULL" or val is None:
        return None
    return val


def create_or_update_ba(ba_to_load, bas_dict):
    if ba_to_load["parent_id"]:
        parent_id = ba_to_load["parent_id"]
        if not BenthicAttribute.objects.filter(pk=parent_id).exists():
            if parent_id in bas_dict:
                parent_data = bas_dict[parent_id]
                create_or_update_ba(parent_data, bas_dict)
            else:
                raise ValueError(f"Parent id {parent_id} not found.")

    ba = BenthicAttribute.objects.get_or_none(pk=ba_to_load["id"])
    if ba:
        BenthicAttribute.objects.filter(pk=ba_to_load["id"]).update(**ba_to_load)
        print(f"Updated {ba_to_load['id']}")
    else:
        BenthicAttribute.objects.create(**ba_to_load)
        print(f"Created {ba_to_load['id']}")


def run():
    ba_csv = Path(settings.BASE_DIR, "data", "benthic_attribute.csv")

    with open(ba_csv) as ba_csv_file:
        ba_csv_reader = csv.DictReader(ba_csv_file)
        bas_dict = {}

        for ba_row in ba_csv_reader:
            kwargs = dict(
                id=str(ba_row["id"]),
                created_on=ba_row["created_on"],
                updated_on=ba_row["updated_on"],
                status=ba_row["status"],
                name=ba_row["name"],
                parent_id=_val_or_none(ba_row["parent_id"]),
                # don't bother with profiles that may not exist in target db
                updated_by_id=None,
                created_by_id=None,
            )
            bas_dict[kwargs["id"]] = kwargs

        for ba_id in list(bas_dict):
            try:
                create_or_update_ba(bas_dict[ba_id], bas_dict)
            except IntegrityError as e:
                print(f"Failed to create or update {ba_id} due to IntegrityError: {e}")
            except ValueError as e:
                print(f"Error: {e}")
