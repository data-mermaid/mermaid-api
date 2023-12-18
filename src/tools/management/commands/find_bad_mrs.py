import csv
import os
from datetime import datetime

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q

from api.models import Management, Project, ProjectProfile


def admin_list(proj):
    pps = ProjectProfile.objects.filter(project=proj, role=ProjectProfile.ADMIN).select_related(
        "profile"
    )
    return ", ".join(["{} <{}>".format(p.profile.full_name, p.profile.email) for p in pps])


class Command(BaseCommand):
    help = """Find and export to csv management regimes with rules that need to be investigated:
    - any rule = False
    - no-take = True and anything else also = True
    - open_access = True and anything else also = True
    """

    def __init__(self):
        super(Command, self).__init__()
        self.exclude_test = False
        self.outpath = ""
        self.header = [
            "name",
            "secondary name",
            "project",
            "project admins",
            "year est",
            "open_access",
            "periodic_closure",
            "size_limits",
            "gear_restriction",
            "species_restriction",
            "no_take",
            "access_restriction",
        ]

    def add_arguments(self, parser):
        parser.add_argument(
            "-t",
            "--notest",
            action="store_true",
            default=False,
            help="Exclude MRs associated with projects marked Test",
        )
        parser.add_argument(
            "-o",
            "--output_path",
            default="",
            help="Provide a custom output dir path to output csv files",
        )

    def write_csv(self, filelabel, mrs):
        ts = datetime.utcnow().strftime("%Y%m%d")
        basefilename = "suspect_mrs_{}_{}.csv"
        mr_path = os.path.join(self.outpath, basefilename.format(filelabel, ts))

        with open(mr_path, "w") as csvfile:
            csvwriter = csv.writer(csvfile)

            csvwriter.writerow(self.header)
            for m in mrs:
                csvwriter.writerow(
                    [
                        m.name,
                        m.name_secondary,
                        m.project.name,
                        admin_list(m.project),
                        m.est_year,
                        m.open_access,
                        m.periodic_closure,
                        m.size_limits,
                        m.gear_restriction,
                        m.species_restriction,
                        m.access_restriction,
                        m.no_take,
                    ]
                )

    def handle(self, *args, **options):
        self.exclude_test = options.get("notest", False)
        self.outpath = options.get("output_path", "")
        if self.outpath == "":
            self.outpath = os.path.join(settings.BASE_DIR, "data")
            if not os.path.isdir(os.path.join(settings.BASE_DIR, "data")):
                os.mkdir(os.path.join(settings.BASE_DIR, "data"))

        # any rule = False
        falses = Management.objects.filter(
            Q(no_take=False)
            | Q(periodic_closure=False)
            | Q(open_access=False)
            | Q(size_limits=False)
            | Q(gear_restriction=False)
            | Q(species_restriction=False)
            | Q(access_restriction=False)
        )

        # no-take = True and anything else also = True
        notake_contras = Management.objects.filter(
            Q(no_take=True)
            & (
                Q(periodic_closure=True)
                | Q(open_access=True)
                | Q(size_limits=True)
                | Q(gear_restriction=True)
                | Q(species_restriction=True)
                | Q(access_restriction=True)
            )
        )

        # open_access = True and anything else also = True
        openaccess_contras = Management.objects.filter(
            Q(open_access=True)
            & (
                Q(periodic_closure=True)
                | Q(no_take=True)
                | Q(size_limits=True)
                | Q(gear_restriction=True)
                | Q(species_restriction=True)
                | Q(access_restriction=True)
            )
        )

        if self.exclude_test:
            falses = falses.exclude(project__status=Project.TEST)
            notake_contras = notake_contras.exclude(project__status=Project.TEST)
            openaccess_contras = openaccess_contras.exclude(project__status=Project.TEST)

        self.write_csv("anyfalse", falses)
        self.write_csv("notake_contras", notake_contras)
        self.write_csv("openaccess_contras", openaccess_contras)
