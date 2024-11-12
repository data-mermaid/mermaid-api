import datetime
from datetime import date

import pytz
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models

from .base import BaseModel
from .mermaid import Project


def validate_unique_elements(value):
    if len(value) != len(set(value)):
        raise ValidationError("Array elements must be unique.")


class GFCRIndicatorSet(BaseModel):
    INDICATOR_SET_TYPE_CHOICES = (
        ("report", "Report"),
        ("target", "Target"),
    )
    INDICATOR_SET_TYPE_CHOICES_UPDATED_ON = datetime.datetime(2024, 5, 27, 0, 0, 0, 0, pytz.UTC)

    title = models.CharField(max_length=100)
    report_date = models.DateField()
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    indicator_set_type = models.CharField(max_length=50, choices=INDICATOR_SET_TYPE_CHOICES)
    f1_1 = models.DecimalField(
        max_digits=9,
        decimal_places=3,
        verbose_name="Total area of coral reefs in GFCR Programme (sq.km)",
        default=0,
    )
    f1_notes = models.TextField(blank=True)
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
    f2_5 = models.DecimalField(
        max_digits=9,
        decimal_places=3,
        verbose_name="Area of non-coral reef ecosystems, e.g., mangroves, seagrass or other associated ecosystems (sq.km)",
        default=0,
    )
    f2_notes = models.TextField(blank=True)
    f3_1 = models.DecimalField(
        max_digits=9,
        decimal_places=3,
        verbose_name="Area of effective coral reef restoration (sq.km)",
        default=0,
    )
    f3_2 = models.PositiveSmallIntegerField(
        verbose_name="Number of in situ coral reef restoration projects", default=0
    )
    f3_3 = models.PositiveSmallIntegerField(
        verbose_name="Number of coral reef restoration plans, technologies, strategies or guidelines developed",
        default=0,
    )
    f3_4 = models.PositiveSmallIntegerField(
        verbose_name="Number of coral reef restoration trainings", default=0
    )
    f3_5a = models.PositiveSmallIntegerField(
        verbose_name="Number of people engaged in coral reef restoration [men]", default=0
    )
    f3_5b = models.PositiveSmallIntegerField(
        verbose_name="Number of people engaged in coral reef restoration [women]", default=0
    )
    f3_5c = models.PositiveSmallIntegerField(
        verbose_name="Number of people engaged in coral reef restoration [youth]",
        null=True,
        blank=True,
    )
    f3_5d = models.PositiveSmallIntegerField(
        verbose_name="Number of people engaged in coral reef restoration [indigenous]",
        null=True,
        blank=True,
    )
    f3_6 = models.PositiveSmallIntegerField(
        verbose_name="Number of response plans to support coral reef restoration after severe shocks",
        default=0,
    )
    f3_notes = models.TextField(blank=True)
    f4_1 = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        verbose_name="Average live hard coral cover (%)",
        default=0,
    )
    f4_2 = models.DecimalField(
        max_digits=4, decimal_places=1, verbose_name="Average macroalgae cover (%)", default=0
    )
    f4_3 = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        verbose_name="Median reef fish biomass (kg/ha)",
        default=0,
    )
    f4_start_date = models.DateField(default=date.today)
    f4_end_date = models.DateField(default=date.today)
    f4_notes = models.TextField(blank=True)
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
        verbose_name="Number of local practitioners trained / supported in coral reef conservation and management [men]",
        default=0,
    )
    f5_4b = models.PositiveSmallIntegerField(
        verbose_name="Number of local practitioners trained / supported in coral reef conservation and management [women]",
        default=0,
    )
    f5_4c = models.PositiveSmallIntegerField(
        verbose_name="Number of local practitioners trained / supported in coral reef conservation and management [youth]",
        null=True,
        blank=True,
    )
    f5_4d = models.PositiveSmallIntegerField(
        verbose_name="Number of local practitioners trained / supported in coral reef conservation and management [indigenous]",
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
    f5_notes = models.TextField(blank=True)
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
    f6_notes = models.TextField(blank=True)
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
        verbose_name="Number of governance reforms/policies to support response and recovery to external shocks",
        default=0,
    )
    f7_notes = models.TextField(blank=True)

    class Meta:
        db_table = "gfcr_indicator_set"
        ordering = ["report_date"]


class GFCRFinanceSolution(BaseModel):
    SECTOR_CHOICES = (
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
    )
    SECTOR_CHOICES_UPDATED_ON = datetime.datetime(2024, 5, 27, 0, 0, 0, 0, pytz.UTC)

    SUSTAINABLE_FINANCE_MECHANISM_CHOICES = (
        ("biodiversity_offsets", "Biodiversity offsets"),
        ("blue_bonds", "Blue bonds"),
        ("blue_carbon", "Blue carbon"),
        ("conservation_trust_funds", "Conservation trust funds"),
        ("debt_conversion", "Debt conversion"),
        ("economic_instruments", "Economic instruments (fines, penalties, taxes, subsidies, etc.)"),
        ("financial_guarantees", "Financial guarantees"),
        ("incubator_tecnical_assistance", "Incubator / Technical assistance facility"),
        ("insurance_products", "Insurance products"),
        ("microfinance", "Microfinance / Village Savings and Loans"),
        ("mpa_entry_fees", "MPA entry fees"),
        ("pay_for_success", "Pay for success"),
        ("revolving_finance_facility", "Revolving finance facility"),
        ("sustainable_livelihood_mech", "Sustainable livelihood mechanisms"),
    )
    SUSTAINABLE_FINANCE_MECHANISM_CHOICES_UPDATED_ON = datetime.datetime(
        2024, 5, 27, 0, 0, 0, 0, pytz.UTC
    )

    GFCR_FUNDED = "gfcr_funded"
    NON_GFCR_FUNDED = "non_gfcr_funded"
    INCUBATOR_CHOICES = (
        (GFCR_FUNDED, "Yes: GFCR-funded"),
        (NON_GFCR_FUNDED, "Yes: Non-GFCR-funded"),
    )
    INCUBATOR_CHOICES_UPDATED_ON = datetime.datetime(2024, 5, 28, 0, 0, 0, 0, pytz.UTC)

    indicator_set = models.ForeignKey(
        GFCRIndicatorSet, on_delete=models.CASCADE, related_name="finance_solutions"
    )
    name = models.CharField(max_length=255)
    sector = models.CharField(max_length=50, choices=SECTOR_CHOICES)
    used_an_incubator = models.CharField(
        max_length=50,
        choices=INCUBATOR_CHOICES,
        null=True,
        blank=True,
    )
    local_enterprise = models.BooleanField(default=False)
    sustainable_finance_mechanisms = ArrayField(
        models.CharField(max_length=50, choices=SUSTAINABLE_FINANCE_MECHANISM_CHOICES),
        default=list,
        validators=[validate_unique_elements],
        null=True,
        blank=True,
    )
    gender_smart = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "gfcr_finance_solution"
        ordering = ["created_on"]

    def get_sustainable_finance_mechanisms_display(self):
        """Returns the display names of the finance mechanisms."""
        choice_dict = dict(self.SUSTAINABLE_FINANCE_MECHANISM_CHOICES)
        return [choice_dict.get(value, value) for value in self.sustainable_finance_mechanisms]


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
        max_digits=12,
        decimal_places=2,
        verbose_name="Investment amount in USD",
        default=0,
    )
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "gfcr_investment_source"
        ordering = ["created_on"]


class GFCRRevenue(BaseModel):
    REVENUE_TYPE_CHOICES = (
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
        ("marine_resources_sales", "Natural resource sales (e.g., fisheries or aquaculture)"),
        ("misc_revenue_streams", "Misc. revenue streams"),
        ("sustainable_livelihood_mechanisms", "Other sustainable livelihood mechanisms"),
    )
    REVENUE_TYPE_CHOICES_UPDATED_ON = datetime.datetime(2024, 5, 27, 0, 0, 0, 0, pytz.UTC)

    finance_solution = models.ForeignKey(
        GFCRFinanceSolution, on_delete=models.CASCADE, related_name="revenues"
    )
    revenue_type = models.CharField(max_length=50, choices=REVENUE_TYPE_CHOICES)
    sustainable_revenue_stream = models.BooleanField(default=False)
    revenue_amount = models.DecimalField(
        max_digits=11, decimal_places=2, verbose_name="Revenue amount in USD", default=0
    )
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "gfcr_revenue"
        ordering = ["created_on"]
