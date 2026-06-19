import django.contrib.postgres.fields
from django.db import migrations, models


def assert_phase4_preconditions(apps, schema_editor):
    from django.db import connection

    REMOVED_SECTORS = (
        "fm_biodiversity_credits",
        "fm_blue_carbon_credits",
        "fm_conservation_trust_fund",
        "fm_insurance_mechanisms",
        "fm_mpa_user_fee",
        "fm_resilience_credits",
        "fm_other",
    )
    REMOVED_SFMS = (
        "conservation_trust_funds",
        "incubator_tecnical_assistance",
        "revolving_finance_facility",
    )
    REPORT_TITLES = {"Baseline", "Mid-year report", "End-year report"}
    TARGET_TITLES = {"Phase 1 target", "Mid-term target", "Final target"}
    ALL_VALID_TITLES = REPORT_TITLES | TARGET_TITLES

    violations = []

    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM gfcr_finance_solution WHERE fs_type IS NULL")
        count = cursor.fetchone()[0]
        if count:
            violations.append(f"{count} finance solution(s) have fs_type IS NULL")

        placeholders = ",".join(["%s"] * len(REMOVED_SECTORS))
        cursor.execute(
            f"SELECT COUNT(*) FROM gfcr_finance_solution WHERE sector IN ({placeholders})",
            list(REMOVED_SECTORS),
        )
        count = cursor.fetchone()[0]
        if count:
            violations.append(f"{count} finance solution(s) use deprecated fm_* sector values")

        sfm_placeholders = ",".join(["%s"] * len(REMOVED_SFMS))
        cursor.execute(
            f"SELECT COUNT(*) FROM gfcr_finance_solution"
            f" WHERE sustainable_finance_mechanisms && ARRAY[{sfm_placeholders}]::varchar[]",
            list(REMOVED_SFMS),
        )
        count = cursor.fetchone()[0]
        if count:
            violations.append(f"{count} finance solution(s) contain deprecated SFM values")

        cursor.execute(
            "SELECT COUNT(*) FROM gfcr_investment_source WHERE investment_type = %s",
            ["public_budget"],
        )
        count = cursor.fetchone()[0]
        if count:
            violations.append(f"{count} investment source(s) use deprecated 'public_budget' type")

        cursor.execute("SELECT id, title, indicator_set_type FROM gfcr_indicator_set")
        for iset_id, title, iset_type in cursor.fetchall():
            if title not in ALL_VALID_TITLES:
                violations.append(
                    f"Indicator set {iset_id}: title '{title}' is not a valid canonical title"
                )
            elif iset_type == "report" and title not in REPORT_TITLES:
                violations.append(
                    f"Indicator set {iset_id}: target title '{title}' used with 'report' type"
                )
            elif iset_type == "target" and title not in TARGET_TITLES:
                violations.append(
                    f"Indicator set {iset_id}: report title '{title}' used with 'target' type"
                )

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM gfcr_revenue r
            JOIN gfcr_finance_solution fs ON r.finance_solution_id = fs.id
            WHERE fs.fs_type = 'programmatic_co_financing'
            """
        )
        count = cursor.fetchone()[0]
        if count:
            violations.append(
                f"{count} revenue(s) linked to PCF finance solutions must be deleted first"
            )

    if violations:
        msg = (
            "Phase 4 preconditions not met. "
            "Run 'python manage.py check_gfcr_data' to identify issues:\n"
            + "\n".join(f"  - {v}" for v in violations)
        )
        raise RuntimeError(msg)


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0124_mv_invert_attributes_goi_family_order_class"),
    ]

    operations = [
        migrations.RunPython(assert_phase4_preconditions, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="gfcrfinancesolution",
            name="fs_type",
            field=models.CharField(
                choices=[
                    ("taf", "Technical assistance facility (TAF)"),
                    ("ctf", "Conservation trust fund (CTF)"),
                    ("financial_facility", "Financial facility"),
                    ("business", "Business solution"),
                    ("financial_mechanism", "Financial mechanism solution"),
                    ("programmatic_co_financing", "Programmatic co-financing"),
                ],
                max_length=50,
            ),
        ),
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
        migrations.AlterField(
            model_name="gfcrfinancesolution",
            name="sustainable_finance_mechanisms",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(
                    choices=[
                        ("biodiversity_offsets", "Biodiversity credits"),
                        ("blue_bonds", "Blue bonds"),
                        ("blue_carbon", "Blue carbon credits"),
                        ("debt_conversion", "Debt conversion"),
                        (
                            "economic_instruments",
                            "Economic instruments (fines, penalties, taxes, subsidies, etc.)",
                        ),
                        ("financial_guarantees", "Financial guarantees"),
                        ("insurance_products", "Insurance products"),
                        ("microfinance", "Microfinance / village savings and loans"),
                        ("mpa_entry_fees", "MPA entry fees"),
                        ("pay_for_success", "Pay for success"),
                        ("resilience_credits", "Resilience credits"),
                        ("sustainable_livelihood_mech", "Sustainable livelihood mechanisms"),
                    ],
                    max_length=50,
                ),
                blank=True,
                default=list,
                null=True,
                size=None,
            ),
        ),
        migrations.AlterField(
            model_name="gfcrinvestmentsource",
            name="investment_type",
            field=models.CharField(
                choices=[
                    ("bond", "Bond"),
                    ("commercial_loan", "Commercial loan"),
                    ("concessional_loan", "Concessional loan"),
                    ("equity", "Equity"),
                    ("financial_guarantee", "Financial guarantee"),
                    ("grant", "Grant"),
                    ("technical_assistance", "Technical assistance / in-kind"),
                ],
                max_length=50,
            ),
        ),
        migrations.AlterField(
            model_name="gfcrindicatorset",
            name="title",
            field=models.CharField(
                choices=[
                    ("Baseline", "Baseline"),
                    ("Mid-year report", "Mid-year report"),
                    ("End-year report", "End-year report"),
                    ("Phase 1 target", "Phase 1 target"),
                    ("Mid-term target", "Mid-term target"),
                    ("Final target", "Final target"),
                ],
                max_length=100,
            ),
        ),
    ]
