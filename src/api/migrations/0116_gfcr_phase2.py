from django.db import migrations, models


def convert_sfm_nulls(apps, schema_editor):
    GFCRFinanceSolution = apps.get_model("api", "GFCRFinanceSolution")
    GFCRFinanceSolution.objects.filter(sustainable_finance_mechanisms__isnull=True).update(
        sustainable_finance_mechanisms=[]
    )


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0115_goi_schema_finalize"),
    ]

    operations = [
        migrations.RunPython(convert_sfm_nulls, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="gfcrfinancesolution",
            name="sector",
            field=models.CharField(
                blank=True,
                choices=[
                    (
                        "ce_pollution_mitigation",
                        "Circular Economy and Pollution Management - Pollution Mitigation",
                    ),
                    (
                        "ce_sustainable_infrastructure",
                        "Circular Economy and Pollution Management - Sustainable Infrastructure",
                    ),
                    (
                        "ce_waste_management",
                        "Circular Economy and Pollution Management - Waste Management",
                    ),
                    ("ce_other", "Circular Economy and Pollution Management - Other"),
                    ("fm_biodiversity_credits", "Financial Mechanisms - Biodiversity Credits"),
                    ("fm_blue_carbon_credits", "Financial Mechanisms - Blue Carbon Credits"),
                    (
                        "fm_conservation_trust_fund",
                        "Financial Mechanisms - Conservation Trust Fund",
                    ),
                    ("fm_insurance_mechanisms", "Financial Mechanisms - Insurance Mechanisms"),
                    ("fm_mpa_user_fee", "Financial Mechanisms - MPA User Fee"),
                    ("fm_resilience_credits", "Financial Mechanisms - Resilience Credits"),
                    ("fm_other", "Financial Mechanisms - Other"),
                    (
                        "sc_coastal_infrastructure",
                        "Sustainable Coastal Development - Coastal Infrastructure",
                    ),
                    (
                        "sc_coral_restoration_revenue_models",
                        "Sustainable Coastal Development - Coral Restoration Revenue Models",
                    ),
                    ("sc_ecotourism", "Sustainable Coastal Development - Ecotourism"),
                    ("sc_other", "Sustainable Coastal Development - Other"),
                    ("so_aquaculture", "Sustainable Ocean Production - Aquaculture"),
                    ("so_fisheries", "Sustainable Ocean Production - Fisheries"),
                    ("so_mariculture", "Sustainable Ocean Production - Mariculture"),
                    (
                        "so_marine_biotechnology_products",
                        "Sustainable Ocean Production - Marine Biotechnology Products",
                    ),
                    ("so_other", "Sustainable Ocean Production - Other"),
                    (
                        "so_sustainable_small_scale_fisheries",
                        "Sustainable Ocean Production - Sustainable Small-Scale Fisheries",
                    ),
                ],
                default="",
                max_length=50,
            ),
        ),
        migrations.AddField(
            model_name="gfcrfinancesolution",
            name="fs_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("taf", "Technical assistance facility (TAF)"),
                    ("ctf", "Conservation trust fund (CTF)"),
                    ("financial_facility", "Financial facility"),
                    ("business", "Business solution"),
                    ("financial_mechanism", "Financial mechanism solution"),
                    ("programmatic_co_financing", "Programmatic co-financing"),
                ],
                max_length=50,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="gfcrfinancesolution",
            name="geographical_coverage",
            field=models.CharField(
                blank=True,
                choices=[
                    ("regional", "Regional"),
                    ("national", "National"),
                    ("subnational", "Subnational"),
                ],
                default="",
                max_length=50,
            ),
        ),
        migrations.AddField(
            model_name="gfcrfinancesolution",
            name="taf_name",
            field=models.CharField(
                blank=True,
                default="",
                max_length=255,
                verbose_name="Name of TAF (incubator)",
            ),
        ),
        migrations.AddField(
            model_name="gfcrfinancesolution",
            name="number_of_solutions_supported_by",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name="gfcrfinancesolution",
            name="used_an_incubator",
            field=models.CharField(
                blank=True,
                choices=[
                    ("gfcr_funded", "Yes: GFCR-funded"),
                    ("non_gfcr_funded", "Yes: Non-GFCR-funded"),
                ],
                max_length=50,
                null=True,
                verbose_name="Used a TAF (incubator)",
            ),
        ),
    ]
