import argparse
import csv
import uuid

from django.core.management.base import BaseCommand

from api.models import (
    BENTHICLIT_PROTOCOL,
    BENTHICPIT_PROTOCOL,
    BLEACHINGQC_PROTOCOL,
    GrowthForm,
    ObsBenthicPIT,
)
from api.utils.timer import timing


class Command(BaseCommand):
    protocol_choices = (BENTHICPIT_PROTOCOL, BLEACHINGQC_PROTOCOL, BENTHICLIT_PROTOCOL)

    def add_arguments(self, parser):
        parser.add_argument("csvfile", nargs=1, type=argparse.FileType("r"))
        parser.add_argument("out_csv_file", nargs=1, type=argparse.FileType("w"))
        parser.add_argument("project", nargs=1, type=uuid.UUID)
        parser.add_argument("--protocol", choices=self.protocol_choices)
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Dry run of repairing growth forms.",
        )

    def create_key(
        self,
        site,
        management,
        transect_number,
        sample_date,
        depth,
        obs_interval,
        benthic_attr,
    ):
        depth = f"{float(depth):.1f}"
        obs_interval = f"{float(obs_interval):.1f}"
        return f"{site}:::{management}:::{transect_number}:::{sample_date}:::{depth}:::{obs_interval}:::{benthic_attr}".lower()

    def _create_csv_lookup(self, csv_file):
        lookup = dict()
        csv_reader = csv.DictReader(csv_file)
        try:
            for row in csv_reader:
                site = row["Site *"]
                management = row["Management *"]
                transect_number = row["Transect number *"]
                depth = row["Depth *"]
                obs_interval = f'{float(row["Observation interval *"]):.2f}'
                benthic_attr = row["Benthic attribute *"]
                sample_date = f'{row["Sample date: Year *"]}-{row["Sample date: Month *"]}-{row["Sample date: Day *"]}'

                key = self.create_key(
                    site,
                    management,
                    transect_number,
                    sample_date,
                    depth,
                    obs_interval,
                    benthic_attr,
                )
                lookup[key] = row
        finally:
            csv_file.close()

        return csv_reader.fieldnames, lookup

    def _create_benthic_pit_model_lookup(self, project_id):
        qry = {ObsBenthicPIT.project_lookup: project_id}
        obs = ObsBenthicPIT.objects.select_related(
            "benthicpit",
            "benthicpit__transect",
            "benthicpit__transect__sample_event",
            "benthicpit__transect__sample_event__site",
            "benthicpit__transect__sample_event__management",
        ).filter(**qry)
        lookup = dict()
        for ob in obs:
            transect = ob.benthicpit.transect
            se = transect.sample_event
            site = se.site.name
            management = se.management.name
            transect_number = transect.number
            depth = transect.depth
            sample_date = f"{se.sample_date.year}-{se.sample_date.month}-{se.sample_date.day}"
            obs_interval = ob.interval
            benthic_attr = ob.attribute.name
            key = self.create_key(
                site,
                management,
                transect_number,
                sample_date,
                depth,
                obs_interval,
                benthic_attr,
            )
            # if str(ob.id) == "42f42c8b-80b3-4490-a894-32980516c450":
            #     print(key)
            #     exit()

            lookup[key] = ob

        # with open("dump.txt", "w") as w:
        #     for k in lookup:
        #         if "mm1:::vatuira_open:::6:::2013-9-15" in k:
        #             w.write(f"{k}\n")

        return lookup

    def _growth_form_lookup(self):
        return {str(gf.name).lower(): gf.id for gf in GrowthForm.objects.all()}

    @timing
    def handle(self, *args, **options):
        csv_file = options["csvfile"][0]
        out_csv_file = options["out_csv_file"][0]
        project_id = options["project"][0]
        protocol = options["protocol"]
        is_dry_run = options.get("dry_run") or False

        fieldnames, csv_lookup = self._create_csv_lookup(csv_file)
        if protocol == BENTHICPIT_PROTOCOL:
            obs_lookup = self._create_benthic_pit_model_lookup(project_id)
        else:
            raise ValueError("Not supported protocol")

        gf_lookup = self._growth_form_lookup()

        num_fails = 0
        num_success = 0

        fieldnames.append("_status_")
        csv_writer = csv.DictWriter(out_csv_file, fieldnames, dialect="excel")
        csv_writer.writeheader()
        for key, row in csv_lookup.items():
            obs = obs_lookup.get(key)
            if obs is None:
                row["_status_"] = "FAIL"
                csv_writer.writerow(row)
                num_fails += 1
                continue

            growth_form = row["Growth form"] or None
            if growth_form is None:
                row["_status_"] = "SUCCESS"
                csv_writer.writerow(row)
                num_success += 1
                continue

            growth_form_id = gf_lookup.get(growth_form.lower())
            if is_dry_run is False:
                obs.growth_form_id = growth_form_id
                obs.save()
            num_success += 1
            row["_status_"] = "SUCCESS"
            csv_writer.writerow(row)

        print(f"num_fails: {num_fails}")
        print(f"num_success: {num_success}")
