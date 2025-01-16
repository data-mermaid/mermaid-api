import csv

from api.models import GFCRFinanceSolution, Project, ProjectProfile

output_file = "gfcr_extant_sectors_to_remove.csv"


def run():
    extant_fs = GFCRFinanceSolution.objects.filter(
        sector__in=[
            "banking_and_finance",
            "clean_energy",
            "coastal_agriculture",
            "coastal_forestry",
            "coral_ecosystem_restoration",
            "green_shipping_and_cruise_ships",
            "invasive_species_management",
            "sewage_and_waste_water_treatment",
            "water_provision",
        ],
        # indicator_set__project__status__gte=Project.OPEN
    )

    with open(output_file, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "FS name",
                "FS sector",
                "Indicator Set",
                "IS date",
                "Project",
                "Test",
                "Project admins",
            ]
        )

        for fs in extant_fs:
            fs_project = fs.indicator_set.project
            is_test = "yes" if fs_project.status <= Project.TEST else "no"
            fs_admins = ProjectProfile.objects.filter(
                project=fs_project, role__gte=ProjectProfile.ADMIN
            )
            fs_admin_values = [
                f"{admin.profile.full_name} <{admin.profile.email}>" for admin in fs_admins
            ]
            writer.writerow(
                [
                    fs.name,
                    fs.sector,
                    fs.indicator_set.title,
                    fs.indicator_set.report_date,
                    fs_project.name,
                    is_test,
                    ", ".join(fs_admin_values),
                ]
            )

    print(f"Report generated: {output_file}")
