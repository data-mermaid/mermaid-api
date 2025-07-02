import csv  # noqa: F401
import re  # noqa: F401

from api.models import GFCRFinanceSolution, Project, ProjectProfile  # noqa: F401

output_file = "gfcr_extant_sectors_to_remove.csv"


def run():
    # create new choices for insertion
    # sectors = [
    #     "Circular Economy and Pollution Management - Pollution Mitigation",
    #     "Circular Economy and Pollution Management - Sustainable Infrastructure",
    #     "Circular Economy and Pollution Management - Waste Management",
    #     "Circular Economy and Pollution Management - Other",
    #     "Financial Mechanisms - Biodiversity Credits",
    #     "Financial Mechanisms - Blue Carbon Credits",
    #     "Financial Mechanisms - Conservation Trust Fund",
    #     "Financial Mechanisms - Insurance Mechanisms",
    #     "Financial Mechanisms - MPA User Fee",
    #     "Financial Mechanisms - Resilience Credits",
    #     "Financial Mechanisms - Other",
    #     "Sustainable Coastal Development - Coastal Infrastructure",
    #     "Sustainable Coastal Development - Coral Restoration Revenue Models",
    #     "Sustainable Coastal Development - Ecotourism",
    #     "Sustainable Coastal Development - Other",
    #     "Sustainable Ocean Production - Aquaculture",
    #     "Sustainable Ocean Production - Fisheries",
    #     "Sustainable Ocean Production - Mariculture",
    #     "Sustainable Ocean Production - Marine Biotechnology Products",
    #     "Sustainable Ocean Production - Other",
    #     "Sustainable Ocean Production - Sustainable Small-Scale Fisheries",
    # ]
    #
    # def to_snake_case(text):
    #     return re.sub(r"\W+", "_", text.lower()).strip("_")
    #
    # formatted_entries = []
    # for sector in sectors:
    #     part1, part2 = sector.split(" - ")
    #     combined_snake_case_key = to_snake_case(part1) + "_" + to_snake_case(part2)
    #     formatted_entries.append(f'("{combined_snake_case_key}", "{sector}")')
    #
    # for entry in formatted_entries:
    #     print(f"        {entry},")

    # identify extant uses of sectors for removal
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
            #
            "coastal_infrastructure",
            "ecotourism",
            "marine_protected_areas",
            "other_land_based_pollutants_management",
            "plastic_waste_management",
            "sustainable_fisheries",
            "sustainable_mariculture_aquaculture",
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
