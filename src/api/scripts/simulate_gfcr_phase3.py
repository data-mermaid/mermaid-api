"""
Simulate a completed Phase 3 GFCR data migration and assert Phase 4 readiness.

Usage:
    docker exec -it api_service python manage.py runscript simulate_gfcr_phase3

What it does:
  1. Normalizes indicator set titles to valid TITLE_CHOICES values.
  2. Assigns an fs_type to every finance solution, cycling through all six types so
     every coercion path is exercised at least once. Required fields for each type
     (sector for business, geographical_coverage for ctf, number_of_solutions_supported_by
     for taf) are pre-filled with safe defaults before the coercion runs.
  3. Replaces deprecated choice values (fm_* sectors → ce_other, removed SFMs dropped,
     public_budget investment type → grant).
  4. All finance solution changes go through GFCRFinanceSolutionSerializer.validate() so
     the same coercion logic Collect would trigger is exercised and any unexpected
     ValidationErrors surface here rather than during Phase 3.
  5. Asserts all Phase 4 preconditions — if step 5 prints PASS, Phase 4 is safe to deploy.

Requires: migration 0116 applied (Phase 2 deployed). Run on a local DB only.
"""

from collections import defaultdict

from rest_framework.exceptions import ValidationError

from api.models import GFCRFinanceSolution, GFCRIndicatorSet, GFCRInvestmentSource
from api.resources.gfcr import GFCRFinanceSolutionSerializer

_FS_TYPES = [
    "business",
    "ctf",
    "financial_facility",
    "financial_mechanism",
    "taf",
    "programmatic_co_financing",
]

_REMOVED_SECTOR_VALUES = frozenset(
    {
        "fm_biodiversity_credits",
        "fm_blue_carbon_credits",
        "fm_conservation_trust_fund",
        "fm_insurance_mechanisms",
        "fm_mpa_user_fee",
        "fm_resilience_credits",
        "fm_other",
    }
)

_REMOVED_SFM_VALUES = frozenset(
    {
        "conservation_trust_funds",
        "incubator_tecnical_assistance",
        "revolving_finance_facility",
    }
)

_REPORT_TITLES = frozenset({"Baseline", "Mid-year report", "End-year report"})
_TARGET_TITLES = frozenset({"Phase 1 target", "Mid-term target", "Final target"})
_ALL_VALID_TITLES = _REPORT_TITLES | _TARGET_TITLES


def run():
    log = defaultdict(list)
    errors = defaultdict(list)

    print("=== Phase 3 simulation ===\n")

    _fix_titles(log, errors)
    _assign_types(log, errors)
    _fix_investment_types(log, errors)

    _print_log(log, errors)

    print("Phase 4 readiness:")
    _assert_phase4_ready()


# ---------------------------------------------------------------------------
# Step 1 — indicator set titles
# ---------------------------------------------------------------------------


def _fix_titles(log, errors):
    print("1. Normalizing indicator set titles...")
    for iset in GFCRIndicatorSet.objects.select_related("project").order_by("project__name"):
        title = iset.title
        itype = iset.indicator_set_type

        if itype == "report" and title in _REPORT_TITLES:
            continue
        if itype == "target" and title in _TARGET_TITLES:
            continue

        new_title = "Baseline" if itype == "report" else "Phase 1 target"
        iset.title = new_title
        iset.save(update_fields=["title"])
        log[iset.project.name].append(f"  IS title: {title!r} → {new_title!r}")


# ---------------------------------------------------------------------------
# Step 2 — finance solution types and field coercion
# ---------------------------------------------------------------------------


def _assign_types(log, errors):
    print("2. Assigning finance solution types and coercing fields...")
    serializer = GFCRFinanceSolutionSerializer()

    fss = list(
        GFCRFinanceSolution.objects.select_related("indicator_set__project").order_by(
            "indicator_set__project__name", "indicator_set__report_date", "created_on"
        )
    )

    for idx, fs in enumerate(fss):
        pname = fs.indicator_set.project.name
        fs_type = _FS_TYPES[idx % len(_FS_TYPES)]

        # Clean deprecated values before coercion runs
        sector = "ce_other" if fs.sector in _REMOVED_SECTOR_VALUES else fs.sector
        sfms = [
            s for s in (fs.sustainable_finance_mechanisms or []) if s not in _REMOVED_SFM_VALUES
        ]

        # Pre-fill required fields so validate() doesn't error on missing values
        geo = fs.geographical_coverage or ("national" if fs_type == "ctf" else "")
        num = fs.number_of_solutions_supported_by
        if fs_type == "business" and not sector:
            sector = "ce_other"
        elif fs_type == "taf" and num == 0:
            num = 1

        data = {
            "fs_type": fs_type,
            "sector": sector,
            "geographical_coverage": geo,
            "used_an_incubator": fs.used_an_incubator,
            "taf_name": fs.taf_name,
            "local_enterprise": fs.local_enterprise,
            "gender_smart": fs.gender_smart,
            "number_of_solutions_supported_by": num,
            "sustainable_finance_mechanisms": sfms,
            "notes": fs.notes,
        }

        # PCF strands revenues — delete them first, as a Phase 3 user must do manually.
        if fs_type == "programmatic_co_financing":
            revenue_count = fs.revenues.count()
            if revenue_count:
                fs.revenues.all().delete()
                log[pname].append(
                    f"  FS {fs.name!r}: deleted {revenue_count} revenue(s) before setting PCF"
                    f" (PCF disables revenue access — revenues must be removed first)"
                )

        try:
            coerced = serializer.validate(dict(data))
        except ValidationError as e:
            errors[pname].append(f"  FS {fs.name!r} (→ {fs_type}): {e.detail}")
            continue

        fs.fs_type = coerced["fs_type"]
        fs.sector = coerced["sector"]
        fs.geographical_coverage = coerced["geographical_coverage"]
        fs.used_an_incubator = coerced["used_an_incubator"]
        fs.taf_name = coerced["taf_name"]
        fs.local_enterprise = coerced["local_enterprise"]
        fs.gender_smart = coerced["gender_smart"]
        fs.number_of_solutions_supported_by = coerced["number_of_solutions_supported_by"]
        fs.sustainable_finance_mechanisms = coerced["sustainable_finance_mechanisms"]
        fs.save()

        log[pname].append(f"  FS {fs.name!r} → {fs_type}")


# ---------------------------------------------------------------------------
# Step 3 — deprecated investment types
# ---------------------------------------------------------------------------


def _fix_investment_types(log, errors):
    print("3. Replacing deprecated investment types...")
    qs = GFCRInvestmentSource.objects.filter(investment_type="public_budget").select_related(
        "finance_solution__indicator_set__project"
    )
    for inv in qs:
        pname = inv.finance_solution.indicator_set.project.name
        log[pname].append(f"  Investment in {inv.finance_solution.name!r}: public_budget → grant")
    qs.update(investment_type="grant")


# ---------------------------------------------------------------------------
# Output and Phase 4 assertions
# ---------------------------------------------------------------------------


def _print_log(log, errors):
    all_projects = sorted(set(list(log) + list(errors)))
    if not all_projects:
        print("\nNo changes needed.\n")
        return
    print()
    for pname in all_projects:
        print(pname)
        for entry in log.get(pname, []):
            print(entry)
        for entry in errors.get(pname, []):
            print(f"  ERROR: {entry}")
        print()


def _assert_phase4_ready():
    issues = []

    for fs in GFCRFinanceSolution.objects.select_related("indicator_set__project"):
        pname = fs.indicator_set.project.name
        name = fs.name
        if not fs.fs_type:
            issues.append(f"[{pname}] FS {name!r}: fs_type not set")
        if fs.sector in _REMOVED_SECTOR_VALUES:
            issues.append(f"[{pname}] FS {name!r}: deprecated sector {fs.sector!r}")
        for sfm in fs.sustainable_finance_mechanisms or []:
            if sfm in _REMOVED_SFM_VALUES:
                issues.append(f"[{pname}] FS {name!r}: deprecated SFM {sfm!r}")

    for inv in GFCRInvestmentSource.objects.select_related(
        "finance_solution__indicator_set__project"
    ):
        if inv.investment_type == "public_budget":
            pname = inv.finance_solution.indicator_set.project.name
            issues.append(
                f"[{pname}] investment in {inv.finance_solution.name!r}: deprecated 'public_budget'"
            )

    for iset in GFCRIndicatorSet.objects.select_related("project"):
        pname = iset.project.name
        title = iset.title
        if title not in _ALL_VALID_TITLES:
            issues.append(f"[{pname}] IS {title!r}: not in TITLE_CHOICES")
        elif iset.indicator_set_type == "report" and title not in _REPORT_TITLES:
            issues.append(f"[{pname}] IS {title!r}: target title on a report IS")
        elif iset.indicator_set_type == "target" and title not in _TARGET_TITLES:
            issues.append(f"[{pname}] IS {title!r}: report title on a target IS")

    if issues:
        print(f"  FAIL — {len(issues)} issue(s):\n")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("  PASS — all preconditions met, Phase 4 is safe to deploy")
