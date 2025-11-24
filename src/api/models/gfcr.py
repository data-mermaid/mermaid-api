import datetime
from datetime import date

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
    INDICATOR_SET_TYPE_CHOICES_UPDATED_ON = datetime.datetime(
        2024, 5, 27, 0, 0, 0, 0, tzinfo=datetime.timezone.utc
    )

    title = models.CharField(max_length=100)
    report_date = models.DateField()
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    indicator_set_type = models.CharField(max_length=50, choices=INDICATOR_SET_TYPE_CHOICES)
    f1_1 = models.DecimalField(
        max_digits=11,
        decimal_places=5,
        verbose_name="Total area of coral reefs in GFCR Programme (sq.km)",
        default=0,
    )
    f1_notes = models.TextField(blank=True)
    f2_1a = models.DecimalField(
        max_digits=11,
        decimal_places=5,
        verbose_name="Area of MPAs and OECMs (as aligned to GBF Target 3) [coralreef] (sq.km)",
        default=0,
    )
    f2_1b = models.DecimalField(
        max_digits=11,
        decimal_places=5,
        verbose_name="Area of MPAs and OECMs (as aligned to GBF Target 3) [total] (sq.km)",
        default=0,
    )
    f2_2a = models.DecimalField(
        max_digits=11,
        decimal_places=5,
        verbose_name="Area of locally managed areas / co-managed areas [coralreef] (sq.km)",
        default=0,
    )
    f2_2b = models.DecimalField(
        max_digits=11,
        decimal_places=5,
        verbose_name="Area of locally managed areas / co-managed areas [total] (sq.km)",
        default=0,
    )
    f2_3a = models.DecimalField(
        max_digits=11,
        decimal_places=5,
        verbose_name="Area of fisheries management [coralreef] (sq.km)",
        default=0,
    )
    f2_3b = models.DecimalField(
        max_digits=11,
        decimal_places=5,
        verbose_name="Area of fisheries management [total] (sq.km)",
        default=0,
    )
    f2_4 = models.DecimalField(
        max_digits=11,
        decimal_places=5,
        verbose_name="Area with pollution mitigation (sq.km)",
        default=0,
    )
    f2_5 = models.DecimalField(
        max_digits=11,
        decimal_places=5,
        verbose_name="Area of non-coral reef ecosystems, e.g., mangroves, seagrass or other associated ecosystems (sq.km)",
        default=0,
    )
    f2_notes = models.TextField(blank=True)
    f3_1 = models.DecimalField(
        max_digits=11,
        decimal_places=5,
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
        default=0,
    )
    f3_5d = models.PositiveSmallIntegerField(
        verbose_name="Number of people engaged in coral reef restoration [indigenous]",
        default=0,
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
        verbose_name="Average reef fish biomass (kg/ha)",
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
        verbose_name="Number of local scientific/research partners involved in strengthening capacity for participation and co-development",
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
        default=0,
    )
    f5_4d = models.PositiveSmallIntegerField(
        verbose_name="Number of local practitioners trained / supported in coral reef conservation and management [indigenous]",
        default=0,
    )
    f5_5 = models.PositiveSmallIntegerField(
        verbose_name="Number of agreements with local authorities or fishing cooperatives to manage marine resources",
        default=0,
    )
    f5_6 = models.PositiveSmallIntegerField(
        verbose_name="Number of national policies linked to GFCR engagement",
        default=0,
    )
    f5_notes = models.TextField(blank=True)
    f6_1a = models.IntegerField(
        verbose_name="Number of direct jobs created (disaggregated by gender, youth, Indigenous peoples) [men]",
        default=0,
    )
    f6_1b = models.IntegerField(
        verbose_name="Number of direct jobs created (disaggregated by gender, youth, Indigenous peoples) [women]",
        default=0,
    )
    f6_1c = models.IntegerField(
        verbose_name="Number of direct jobs created (disaggregated by gender, youth, Indigenous peoples) [youth]",
        default=0,
    )
    f6_1d = models.IntegerField(
        verbose_name="Number of direct jobs created (disaggregated by gender, youth, Indigenous peoples) [indigenous]",
        default=0,
    )
    f6_notes = models.TextField(blank=True)
    f7_1a = models.IntegerField(
        verbose_name="Total direct beneficiaries (disaggregated by gender, youth, Indigenous peoples) [men]",
        default=0,
    )
    f7_1b = models.IntegerField(
        verbose_name="Total direct beneficiaries (disaggregated by gender, youth, Indigenous peoples) [women]",
        default=0,
    )
    f7_1c = models.IntegerField(
        verbose_name="Total direct beneficiaries (disaggregated by gender, youth, Indigenous peoples) [youth]",
        default=0,
    )
    f7_1d = models.IntegerField(
        verbose_name="Total direct beneficiaries (disaggregated by gender, youth, Indigenous peoples) [indigenous]",
        default=0,
    )
    f7_2a = models.IntegerField(
        verbose_name="Total indirect beneficiaries (disaggregated by gender, youth, Indigenous peoples) [men]",
        default=0,
    )
    f7_2b = models.IntegerField(
        verbose_name="Total indirect beneficiaries (disaggregated by gender, youth, Indigenous peoples) [women]",
        default=0,
    )
    f7_2c = models.IntegerField(
        verbose_name="Total indirect beneficiaries (disaggregated by gender, youth, Indigenous peoples) [youth]",
        default=0,
    )
    f7_2d = models.IntegerField(
        verbose_name="Total indirect beneficiaries (disaggregated by gender, youth, Indigenous peoples) [indigenous]",
        default=0,
    )
    f7_3 = models.PositiveSmallIntegerField(
        verbose_name="Number of financial mechanisms/reforms to help coastal communities respond and recover from external shocks",
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
        (
            "ce_pollution_mitigation",
            "Circular Economy and Pollution Management - Pollution Mitigation",
        ),
        (
            "ce_sustainable_infrastructure",
            "Circular Economy and Pollution Management - Sustainable Infrastructure",
        ),
        ("ce_waste_management", "Circular Economy and Pollution Management - Waste Management"),
        ("ce_other", "Circular Economy and Pollution Management - Other"),
        ("fm_biodiversity_credits", "Financial Mechanisms - Biodiversity Credits"),
        ("fm_blue_carbon_credits", "Financial Mechanisms - Blue Carbon Credits"),
        ("fm_conservation_trust_fund", "Financial Mechanisms - Conservation Trust Fund"),
        ("fm_insurance_mechanisms", "Financial Mechanisms - Insurance Mechanisms"),
        ("fm_mpa_user_fee", "Financial Mechanisms - MPA User Fee"),
        ("fm_resilience_credits", "Financial Mechanisms - Resilience Credits"),
        ("fm_other", "Financial Mechanisms - Other"),
        ("sc_coastal_infrastructure", "Sustainable Coastal Development - Coastal Infrastructure"),
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
    )
    SECTOR_CHOICES_UPDATED_ON = datetime.datetime(
        2025, 2, 3, 0, 0, 0, 0, tzinfo=datetime.timezone.utc
    )

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
        2024, 5, 27, 0, 0, 0, 0, tzinfo=datetime.timezone.utc
    )

    GFCR_FUNDED = "gfcr_funded"
    NON_GFCR_FUNDED = "non_gfcr_funded"
    INCUBATOR_CHOICES = (
        (GFCR_FUNDED, "Yes: GFCR-funded"),
        (NON_GFCR_FUNDED, "Yes: Non-GFCR-funded"),
    )
    INCUBATOR_CHOICES_UPDATED_ON = datetime.datetime(
        2024, 5, 28, 0, 0, 0, 0, tzinfo=datetime.timezone.utc
    )

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
    INVESTMENT_SOURCE_CHOICES_UPDATED_ON = datetime.datetime(
        2024, 5, 27, 0, 0, 0, 0, tzinfo=datetime.timezone.utc
    )

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
    INVESTMENT_TYPE_CHOICES_UPDATED_ON = datetime.datetime(
        2024, 5, 27, 0, 0, 0, 0, tzinfo=datetime.timezone.utc
    )

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
    REVENUE_TYPE_CHOICES_UPDATED_ON = datetime.datetime(
        2024, 5, 27, 0, 0, 0, 0, tzinfo=datetime.timezone.utc
    )

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
