import datetime
from datetime import date

import pytz
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from .base import BaseModel
from .mermaid import Project


def validate_unique_elements(value):
    if len(value) != len(set(value)):
        raise ValidationError("Array elements must be unique.")


class GFCRIndicatorSet(BaseModel):
    INDICATOR_SET_TYPE_CHOICES = (
        ("annual_report", "Annual Report"),
        ("target", "Target"),
    )
    INDICATOR_SET_TYPE_CHOICES_UPDATED_ON = datetime.datetime(2024, 5, 27, 0, 0, 0, 0, pytz.UTC)

    title = models.CharField(max_length=100)
    report_date = models.DateField()
    report_year = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1900), MaxValueValidator(2100)]
    )
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    indicator_set_type = models.CharField(max_length=50, choices=INDICATOR_SET_TYPE_CHOICES)
    f1_1 = models.DecimalField(
        max_digits=9,
        decimal_places=3,
        verbose_name="Total area of coral reefs in GFCR programming (sq.km)",
        default=0,
    )
    f2_1a = models.DecimalField(
        max_digits=9,
        decimal_places=3,
        verbose_name="Area of MPAs and OECMs (as aligned to GBF Target 3) [coralreef] (sq.km)",
        default=0,
    )
    f2_1b = models.DecimalField(
        max_digits=9,
        decimal_places=3,
        verbose_name="Area of MPAs and OECMs (as aligned to GBF Target 3) [total] (sq.km)",
        default=0,
    )
    f2_2a = models.DecimalField(
        max_digits=9,
        decimal_places=3,
        verbose_name="Area of locally managed areas / co-managed areas [coralreef] (sq.km)",
        default=0,
    )
    f2_2b = models.DecimalField(
        max_digits=9,
        decimal_places=3,
        verbose_name="Area of locally managed areas / co-managed areas [total] (sq.km)",
        default=0,
    )
    f2_3a = models.DecimalField(
        max_digits=9,
        decimal_places=3,
        verbose_name="Area of fisheries management [coralreef] (sq.km)",
        default=0,
    )
    f2_3b = models.DecimalField(
        max_digits=9,
        decimal_places=3,
        verbose_name="Area of fisheries management [total] (sq.km)",
        default=0,
    )
    f2_4 = models.DecimalField(
        max_digits=9,
        decimal_places=3,
        verbose_name="Area with pollution mitigation (sq.km)",
        default=0,
    )
    f2_opt1 = models.DecimalField(
        max_digits=9,
        decimal_places=3,
        verbose_name="Area of non-coral reef ecosystems, e.g., mangroves, seagrass or other associated ecosystems (sq.km)",
        null=True,
        blank=True,
    )
    f3_1 = models.DecimalField(
        max_digits=9,
        decimal_places=3,
        verbose_name="Area of effective coral reef restoration (sq.km)",
        default=0,
    )
    f3_2 = models.PositiveSmallIntegerField(
        verbose_name="Number of in situ coral restoration projects", default=0
    )
    f3_3 = models.PositiveSmallIntegerField(
        verbose_name="Number of coral restoration plans, technologies, strategies or guidelines developed",
        default=0,
    )
    f3_4 = models.PositiveSmallIntegerField(
        verbose_name="Number of coral restoration trainings", default=0
    )
    f3_5a = models.PositiveSmallIntegerField(
        verbose_name="Number of people engaged in coral restoration [men]", default=0
    )
    f3_5b = models.PositiveSmallIntegerField(
        verbose_name="Number of people engaged in coral restoration [women]", default=0
    )
    f3_5c = models.PositiveSmallIntegerField(
        verbose_name="Number of people engaged in coral restoration [youth]",
        null=True,
        blank=True,
    )
    f3_5d = models.PositiveSmallIntegerField(
        verbose_name="Number of people engaged in coral restoration [indigenous]",
        null=True,
        blank=True,
    )
    f3_6 = models.PositiveSmallIntegerField(
        verbose_name="Number of response plans (incl. financial mechanisms, eg., insurance) in place to support coral restoration after severe shocks (e.g,. storms, bleaching)",
        default=0,
    )
    f4_1 = models.DecimalField(
        max_digits=4, decimal_places=1, verbose_name="Average live hard coral cover (%)", default=0
    )
    f4_2 = models.DecimalField(
        max_digits=4, decimal_places=1, verbose_name="Average macroalgae (%)", default=0
    )
    f4_3 = models.DecimalField(
        max_digits=5, decimal_places=1, verbose_name="Median reef fish biomass (kg/ha)", default=0
    )
    f4_start_date = models.DateField(default=date.today)
    f4_end_date = models.DateField(default=date.today)
    f5_1 = models.PositiveSmallIntegerField(
        verbose_name="Number of local communities engaged in meaningful participation and co-development",
        default=0,
    )
    f5_2 = models.PositiveSmallIntegerField(
        verbose_name="Number of local organizations engaged in meaningful participation and co-development",
        default=0,
    )
    f5_3 = models.PositiveSmallIntegerField(
        verbose_name="Number of local scientific/research partners involved in strengthening capacity for participation and co-development (e.g., national universities, regional science organizations)",
        default=0,
    )
    f5_4a = models.PositiveSmallIntegerField(
        verbose_name="Number of local practitioners trained / supported in coral reef conservation (e.g. community rangers) [men]",
        default=0,
    )
    f5_4b = models.PositiveSmallIntegerField(
        verbose_name="Number of local practitioners trained / supported in coral reef conservation (e.g. community rangers) [women]",
        default=0,
    )
    f5_4c = models.PositiveSmallIntegerField(
        verbose_name="Number of local practitioners trained / supported in coral reef conservation (e.g. community rangers) [youth]",
        null=True,
        blank=True,
    )
    f5_4d = models.PositiveSmallIntegerField(
        verbose_name="Number of local practitioners trained / supported in coral reef conservation (e.g. community rangers) [indigenous]",
        null=True,
        blank=True,
    )
    f5_5 = models.PositiveSmallIntegerField(
        verbose_name="Number of agreements with local authorities or fishing cooperatives to manage marine resources (e.g., LMMAs, MPAs, OECMs)",
        default=0,
    )
    f5_6 = models.PositiveSmallIntegerField(
        verbose_name="Number of national policies linked to GFCR engagement, (e.g., NBSAPs, blue economy policies, national MPA declarations)",
        default=0,
    )
    f6_1a = models.PositiveSmallIntegerField(
        verbose_name="Number of direct jobs created (disaggregated by gender, age, Indigenous peoples) [men]",
        default=0,
    )
    f6_1b = models.PositiveSmallIntegerField(
        verbose_name="Number of direct jobs created (disaggregated by gender, age, Indigenous peoples) [women]",
        default=0,
    )
    f6_1c = models.PositiveSmallIntegerField(
        verbose_name="Number of direct jobs created (disaggregated by gender, age, Indigenous peoples) [youth]",
        null=True,
        blank=True,
    )
    f6_1d = models.PositiveSmallIntegerField(
        verbose_name="Number of direct jobs created (disaggregated by gender, age, Indigenous peoples) [indigenous]",
        null=True,
        blank=True,
    )
    f6_2a = models.PositiveSmallIntegerField(
        verbose_name="Number of people with increased income and/or nutrition from GFCR support (disaggregated by gender, age, Indigenous peoples) [men]",
        default=0,
    )
    f6_2b = models.PositiveSmallIntegerField(
        verbose_name="Number of people with increased income and/or nutrition from GFCR support (disaggregated by gender, age, Indigenous peoples) [women]",
        default=0,
    )
    f6_2c = models.PositiveSmallIntegerField(
        verbose_name="Number of people with increased income and/or nutrition from GFCR support (disaggregated by gender, age, Indigenous peoples) [youth]",
        null=True,
        blank=True,
    )
    f6_2d = models.PositiveSmallIntegerField(
        verbose_name="Number of people with increased income and/or nutrition from GFCR support (disaggregated by gender, age, Indigenous peoples) [indigenous]",
        null=True,
        blank=True,
    )
    f7_1a = models.PositiveSmallIntegerField(
        verbose_name="Total direct beneficiaries (disaggregated by gender, age, Indigenous peoples) [men]",
        default=0,
    )
    f7_1b = models.PositiveSmallIntegerField(
        verbose_name="Total direct beneficiaries (disaggregated by gender, age, Indigenous peoples) [women]",
        default=0,
    )
    f7_1c = models.PositiveSmallIntegerField(
        verbose_name="Total direct beneficiaries (disaggregated by gender, age, Indigenous peoples) [youth]",
        null=True,
        blank=True,
    )
    f7_1d = models.PositiveSmallIntegerField(
        verbose_name="Total direct beneficiaries (disaggregated by gender, age, Indigenous peoples) [indigenous]",
        null=True,
        blank=True,
    )
    f7_2a = models.PositiveSmallIntegerField(
        verbose_name="Total indirect beneficiaries (disaggregated by gender, age, Indigenous peoples) [men]",
        default=0,
    )
    f7_2b = models.PositiveSmallIntegerField(
        verbose_name="Total indirect beneficiaries (disaggregated by gender, age, Indigenous peoples) [women]",
        default=0,
    )
    f7_2c = models.PositiveSmallIntegerField(
        verbose_name="Total indirect beneficiaries (disaggregated by gender, age, Indigenous peoples) [youth]",
        null=True,
        blank=True,
    )
    f7_2d = models.PositiveSmallIntegerField(
        verbose_name="Total indirect beneficiaries (disaggregated by gender, age, Indigenous peoples) [indigenous]",
        null=True,
        blank=True,
    )
    f7_3 = models.PositiveSmallIntegerField(
        verbose_name="Number of financial mechanisms/reforms to help coastal communities respond and recover from external shocks (e.g., insurance, loans, village savings, restoration crisis plans, etc)",
        default=0,
    )
    f7_4 = models.PositiveSmallIntegerField(
        verbose_name="Number of governance reforms/policies to support response and recovery to external shocks (e.g., crisis management plans, reforms for temporary alternative employment)",
        default=0,
    )

    class Meta:
        db_table = "gfcr_indicator_set"
        ordering = ["report_date"]


class GFCRFinanceSolution(BaseModel):
    SECTOR_CHOICES = (
        ("clean_energy", "Clean energy"),
        ("coastal_agriculture", "Coastal agriculture"),
        ("coastal_forestry", "Coastal forestry"),
        ("coastal_infrastructure", "Coastal infrastructure"),
        ("coral_ecosystem_restoration", "Coral ecosystem restoration"),
        ("ecotourism", "Ecotourism"),
        ("green_shipping_and_cruise_ships", "Green shipping and cruise ships"),
        ("invasive_species_management", "Invasive species management"),
        ("marine_protected_areas", "Marine protected areas"),
        ("other_land_based_pollutants_management", "Other land-based pollutants management"),
        ("plastic_waste_management", "Plastic waste management"),
        ("sewage_and_waste_water_treatment", "Sewage and waste-water treatment"),
        ("sustainable_fisheries", "Sustainable fisheries"),
        ("sustainable_mariculture_aquaculture", "Sustainable mariculture/aquaculture"),
    )
    SECTOR_CHOICES_UPDATED_ON = datetime.datetime(2024, 5, 27, 0, 0, 0, 0, pytz.UTC)

    SUSTAINABLE_FINANCE_MECHANISM_CHOICES = (
        ("biodiversity_offsets", "Biodiversity offsets"),
        ("blue_bonds", "Blue bonds"),
        ("blue_carbon", "Blue carbon"),
        ("conservation_trust_funds", "Conservation trust funds"),
        ("debt_conversion", "Debt conversion"),
        ("incubator_tecnical_assistance", "Incubator / Technical assistance"),
        ("insurance_products", "Insurance products"),
        ("mpa_entry_fees", "MPA entry fees"),
        ("pay_for_success", "Pay for success"),
        ("sustainable_livelihood_mech", "Sustainable livelihood mechanisms"),
    )
    SUSTAINABLE_FINANCE_MECHANISM_CHOICES_UPDATED_ON = datetime.datetime(2024, 5, 27, 0, 0, 0, 0, pytz.UTC)

    indicator_set = models.ForeignKey(
        GFCRIndicatorSet, on_delete=models.CASCADE, related_name="finance_solutions"
    )
    name = models.CharField(max_length=255)
    sector = models.CharField(max_length=50, choices=SECTOR_CHOICES)
    used_an_incubator = models.BooleanField(default=False)
    local_enterprise = models.BooleanField(default=False)
    sustainable_finance_mechanisms = ArrayField(
        models.CharField(max_length=50, choices=SUSTAINABLE_FINANCE_MECHANISM_CHOICES),
        default=list,
        validators=[validate_unique_elements],
        null=True,
        blank=True,
    )
    gender_smart = models.BooleanField(default=False)

    class Meta:
        db_table = "gfcr_finance_solution"
        ordering = ["created_on"]


class GFCRInvestmentSource(BaseModel):
    INVESTMENT_SOURCE_CHOICES = (
        ("gfcr", "GFCR"),
        ("philanthropy", "Philanthropy"),
        ("private", "Private"),
        ("public", "Public"),
    )
    INVESTMENT_SOURCE_CHOICES_UPDATED_ON = datetime.datetime(2024, 5, 27, 0, 0, 0, 0, pytz.UTC)

    INVESTMENT_TYPE_CHOICES = (
        ("bond", "Bond"),
        ("commercial_loan", "Commercial loan"),
        ("concessional_loan", "Concessional loan"),
        ("equity", "Equity"),
        ("financial_guarantee", "Financial guarantee"),
        ("grant", "Grant"),
        ("public_budget", "Public budget"),
        ("technical_assistance", "Technical assistance"),
    )
    INVESTMENT_TYPE_CHOICES_UPDATED_ON = datetime.datetime(2024, 5, 27, 0, 0, 0, 0, pytz.UTC)

    finance_solution = models.ForeignKey(
        GFCRFinanceSolution, on_delete=models.CASCADE, related_name="investment_sources"
    )
    investment_source = models.CharField(max_length=50, choices=INVESTMENT_SOURCE_CHOICES)
    investment_type = models.CharField(max_length=50, choices=INVESTMENT_TYPE_CHOICES)
    investment_amount = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name="Investment amount in USD", default=0
    )
    used_gfcr_funded_incubator = models.BooleanField(default=False)

    class Meta:
        db_table = "gfcr_investment_source"
        ordering = ["created_on"]


class GFCRRevenue(BaseModel):
    REVENUE_TYPE_CHOICES = (
        ("biodiversity_offsets", "Biodiversity offsets"),
        ("blue_bonds", "Blue bonds"),
        ("business_incubation_and_investment", "Business incubation and investment"),
        ("carbon_credits_environmental_services", "Carbon credits / environmental services"),
        ("conservation_trust_funds", "Conservation trust funds"),
        ("debt_conversion", "Debt conversion"),
        ("ecotourism", "Ecotourism"),
        ("fees_and_payments", "Fees and payments"),
        ("green_tax", "Green tax"),
        ("insurance_products", "Insurance products"),
        ("interest_investment_returns", "Interest / investment returns"),
        ("marine_resources_sales", "Marine resources sales"),
        ("misc_revenue_streams", "Misc. revenue streams"),
        ("sustainable_livelihood_mechanisms", "Sustainable livelihood mechanisms"),
        ("water_tariff", "Water tariff"),
    )
    REVENUE_TYPE_CHOICES_UPDATED_ON = datetime.datetime(2024, 5, 27, 0, 0, 0, 0, pytz.UTC)

    finance_solution = models.ForeignKey(
        GFCRFinanceSolution, on_delete=models.CASCADE, related_name="revenues"
    )
    revenue_type = models.CharField(max_length=50, choices=REVENUE_TYPE_CHOICES)
    sustainable_revenue_stream = models.BooleanField(default=False)
    annual_revenue = models.DecimalField(
        max_digits=11, decimal_places=2, verbose_name="Annual revenue in USD", default=0
    )

    class Meta:
        db_table = "gfcr_revenue"
        ordering = ["created_on"]
