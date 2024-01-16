import csv
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from api.models import APPROVAL_STATUSES, BenthicAttribute, BenthicLifeHistory
from .refresh_base import get_regions


class Command(BaseCommand):
    help = """Insert or update benthic attribute data from csv."""

    def __init__(self):
        super(Command, self).__init__()
        self.source = os.path.join(
            settings.BASE_DIR, "data", "MVP_benthic_list_for_MERMAID_23July2018.csv"
        )
        self.create_only = False

    def add_arguments(self, parser):
        (
            parser.add_argument(
                "-c",
                action="store_true",
                dest="create_only",
                default=False,
                help="Only process create operations, not updates",
            ),
        )

    def benthic_attribute(self, name, parent, nextcol, lh, regions):
        _ = False
        attrib = None
        if name != "":
            benthic_row = {"name": name, "parent": parent, "status": APPROVAL_STATUSES[0][0]}

            try:
                attrib = BenthicAttribute.objects.get(**{"name": name})
                if parent != attrib.parent and not self.create_only:
                    print(
                        "name: %s existing parent: %s new parent: %s"
                        % (name, attrib.parent, parent)
                    )
                    attrib.parent = parent
                    attrib.save()
                    # attrib.regions.add(*regions)
            except BenthicAttribute.DoesNotExist:
                print("create %s" % name)
                attrib, _ = BenthicAttribute.objects.get_or_create(**benthic_row)
            except BenthicAttribute.MultipleObjectsReturned:
                print("multiple objects for %s" % name)

        return attrib, _

    def handle(self, *args, **options):
        self.create_only = options.get("create_only")

        with open(self.source) as benthicdata:
            n = 0
            csvreader = csv.DictReader(benthicdata, delimiter=",")
            for row in csvreader:
                col1 = row["Category"].strip(" \xa0")
                col2 = row["group1"].strip(" \xa0")
                col3 = row["group2"].strip(" \xa0")
                col4 = row["group3"].strip(" \xa0")
                chosen_regions = get_regions((row.get("region") or "").strip(" \xa0"))
                lh = (row.get("life_history") or "").strip(" \xa0")
                if lh != "":
                    life_history = BenthicLifeHistory.objects.get_or_create(name=lh)
                else:
                    life_history = None

                attrib1, c1 = self.benthic_attribute(col1, None, col2, life_history, chosen_regions)
                attrib2, c2 = self.benthic_attribute(
                    col2, attrib1, col3, life_history, chosen_regions
                )
                attrib3, c3 = self.benthic_attribute(
                    col3, attrib2, col4, life_history, chosen_regions
                )
                attrib4, c4 = self.benthic_attribute(
                    col4, attrib3, "", life_history, chosen_regions
                )
                n += sum([c1, c2, c3, c4])

        print("%s coral attributes\n" % (n - 1))
