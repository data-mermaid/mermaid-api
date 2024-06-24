import csv
from pathlib import Path

from django.conf import settings

from api.models import (
    BenthicAttribute,
    BenthicAttributeGrowthFormLifeHistory,
    BenthicLifeHistory,
    GrowthForm,
)


def run():
    ba_csv = Path(settings.BASE_DIR, "data", "BA_LH_AssignmentsWithIDs_20240617.csv")
    ba_gf_csv = Path(settings.BASE_DIR, "data", "Relevant_BA_GF_LH_AssignmentsWithIDs_20240617.csv")

    with open(ba_csv) as ba_csv_file:
        ba_csv_reader = csv.DictReader(ba_csv_file)
        ba_lhs = []
        for ba_lh_row in ba_csv_reader:
            ba_id = str(ba_lh_row["ba_id"])
            ba = BenthicAttribute.objects.get(pk=ba_id)
            lh_id = str(ba_lh_row["lh_id"])
            lh = BenthicLifeHistory.objects.get(pk=lh_id)
            ba_lhs.append((ba, lh))

        for ba_lh in ba_lhs:
            ba_lh[0].life_histories.add(ba_lh[1])

    with open(ba_gf_csv) as ba_gf_csv_file:
        ba_gf_csv_reader = csv.DictReader(ba_gf_csv_file)
        ba_lh_gfs = []
        for ba_gf_row in ba_gf_csv_reader:
            ba_id = str(ba_gf_row["ba_id"])
            ba = BenthicAttribute.objects.get(pk=ba_id)
            gf_id = str(ba_gf_row["gf_id"])
            gf = GrowthForm.objects.get(pk=gf_id)
            lh_id = str(ba_gf_row["lh_id"])
            lh = BenthicLifeHistory.objects.get(pk=lh_id)
            ba_lh_gfs.append((ba, gf, lh))

        for ba_lh_gf in ba_lh_gfs:
            _ = BenthicAttributeGrowthFormLifeHistory.objects.get_or_create(
                attribute=ba_lh_gf[0],
                growth_form=ba_lh_gf[1],
                life_history=ba_lh_gf[2],
            )
