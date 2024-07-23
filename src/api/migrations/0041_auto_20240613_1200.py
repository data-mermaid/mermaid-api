# Generated by Django 3.2.20 on 2024-06-13 12:00

import django.contrib.postgres.fields
from django.db import migrations, models

import api.models.gfcr


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0040_auto_20240523_2232"),
    ]

    operations = [
        migrations.AlterField(
            model_name="gfcrfinancesolution",
            name="sector",
            field=models.CharField(
                choices=[
                    ("banking_and_finance", "Banking and finance"),
                    ("clean_energy", "Clean energy"),
                    ("coastal_agriculture", "Coastal agriculture"),
                    ("coastal_forestry", "Coastal forestry"),
                    ("coastal_infrastructure", "Coastal infrastructure"),
                    ("coral_ecosystem_restoration", "Coral ecosystem restoration"),
                    ("ecotourism", "Ecotourism"),
                    ("green_shipping_and_cruise_ships", "Green shipping and cruise ships"),
                    ("invasive_species_management", "Invasive species management"),
                    (
                        "marine_protected_areas",
                        "Marine Protected Areas and other effectively managed marine areas",
                    ),
                    (
                        "other_land_based_pollutants_management",
                        "Other land-based pollutants management",
                    ),
                    ("plastic_waste_management", "Plastic waste management"),
                    ("sewage_and_waste_water_treatment", "Sewage and waste-water treatment"),
                    ("sustainable_fisheries", "Sustainable fisheries"),
                    ("sustainable_mariculture_aquaculture", "Sustainable mariculture/aquaculture"),
                    ("water_provision", "Water provision"),
                ],
                max_length=50,
            ),
        ),
        migrations.AlterField(
            model_name="gfcrfinancesolution",
            name="sustainable_finance_mechanisms",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(
                    choices=[
                        ("biodiversity_offsets", "Biodiversity offsets"),
                        ("blue_bonds", "Blue bonds"),
                        ("blue_carbon", "Blue carbon"),
                        ("conservation_trust_funds", "Conservation trust funds"),
                        ("debt_conversion", "Debt conversion"),
                        (
                            "economic_instruments",
                            "Economic instruments (fines, penalties, taxes, subsidies, etc.)",
                        ),
                        ("financial_guarantees", "Financial guarantees"),
                        (
                            "incubator_tecnical_assistance",
                            "Incubator / Technical assistance facility",
                        ),
                        ("insurance_products", "Insurance products"),
                        ("microfinance", "Microfinance / Village Savings and Loans"),
                        ("mpa_entry_fees", "MPA entry fees"),
                        ("pay_for_success", "Pay for success"),
                        ("revolving_finance_facility", "Revolving finance facility"),
                        ("sustainable_livelihood_mech", "Sustainable livelihood mechanisms"),
                    ],
                    max_length=50,
                ),
                blank=True,
                default=list,
                null=True,
                size=None,
                validators=[api.models.gfcr.validate_unique_elements],
            ),
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
            ),
        ),
        migrations.AlterField(
            model_name="gfcrrevenue",
            name="revenue_type",
            field=models.CharField(
                choices=[
                    ("biodiversity_offsets", "Biodiversity offsets"),
                    ("blue_bonds", "Blue bonds"),
                    (
                        "carbon_credits_environmental_services",
                        "Carbon credits / environmental services",
                    ),
                    ("conservation_trust_funds", "Conservation trust funds"),
                    ("debt_conversion", "Debt conversion"),
                    ("ecotourism", "Ecotourism sales"),
                    ("fees_and_payments", "Fees, tariffs, penalties, and other payments"),
                    ("green_tax", "Green tax"),
                    ("insurance_products", "Insurance products"),
                    (
                        "interest_investment_returns",
                        "Interest / investment returns (e.g., public, private equity)",
                    ),
                    (
                        "marine_resources_sales",
                        "Natural resource sales (e.g., fisheries or aquaculture)",
                    ),
                    ("misc_revenue_streams", "Misc. revenue streams"),
                    (
                        "sustainable_livelihood_mechanisms",
                        "Other sustainable livelihood mechanisms",
                    ),
                ],
                max_length=50,
            ),
        ),
    ]