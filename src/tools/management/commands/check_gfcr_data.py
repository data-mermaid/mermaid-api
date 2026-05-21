from collections import defaultdict
from datetime import date, datetime

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection, connections

from api.models import GFCRFinanceSolution, GFCRIndicatorSet, Project

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


def _md_table(headers, rows):
    sep = "| " + " | ".join(["---"] * len(headers)) + " |"
    lines = ["| " + " | ".join(headers) + " |", sep]
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines)


class Command(BaseCommand):
    help = "Audit GFCR data for Phase 4 readiness. Restores prod DB locally before running."

    def add_arguments(self, parser):
        parser.add_argument("--project-id", type=str, help="Scope output to a single project UUID")
        parser.add_argument("--output", type=str, help="Override default output file path")

    def handle(self, *args, **options):
        self.stdout.write("Restoring production database...")
        call_command("dbrestore", "prod")

        # dbrestore drops and recreates the DB, which kills any open connection.
        # Close all Django connections so the next operation gets a fresh one.
        connections.close_all()

        self.stdout.write("Applying migrations...")
        call_command("migrate")

        with connection.cursor() as cursor:
            cols = {
                c.name
                for c in connection.introspection.get_table_description(
                    cursor, "gfcr_finance_solution"
                )
            }

        has_type_col = "type" in cols
        has_geo = "geographical_coverage" in cols
        has_taf = "taf_name" in cols
        has_num = "number_of_solutions_supported_by" in cols

        project_id = options.get("project_id")

        is_qs = GFCRIndicatorSet.objects.select_related("project").order_by(
            "project__name", "title"
        )
        if project_id:
            is_qs = is_qs.filter(project_id=project_id)

        fs_qs = (
            GFCRFinanceSolution.objects.select_related("indicator_set__project")
            .prefetch_related("investment_sources")
            .order_by("indicator_set__project__name", "name")
        )
        if project_id:
            fs_qs = fs_qs.filter(indicator_set__project_id=project_id)

        per_project = defaultdict(
            lambda: {"indicator_sets": [], "finance_solutions": [], "investment_sources": []}
        )
        counts = defaultdict(int)

        for pname, title, type_label, check, action, cat in self._check_indicator_sets(is_qs):
            per_project[pname]["indicator_sets"].append((f'"{title}"', type_label, check, action))
            counts[cat] += 1

        for pname, name, section, check, action, cat in self._check_finance_solutions(
            fs_qs, has_type_col, has_geo, has_taf, has_num
        ):
            per_project[pname][section].append((f'"{name}"', check, action))
            counts[cat] += 1

        today_str = date.today().strftime("%Y-%m-%d")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if project_id:
            try:
                proj = Project.objects.get(pk=project_id)
                scope = f"Project: {proj.name}"
            except Project.DoesNotExist:
                scope = f"Project: {project_id}"
        else:
            scope = "all projects"

        total = sum(counts.values())
        n_projects = len(per_project)

        lines = [
            f"# GFCR Data Audit — {today_str}",
            "",
            f"Generated: {now_str}",
            f"Scope: {scope}",
            "",
            "## Summary",
            "",
            (
                f"{total} total issue{'s' if total != 1 else ''} across "
                f"{n_projects} project{'s' if n_projects != 1 else ''}. "
                "Proceed to Phase 4 only when this report shows no issues."
            ),
            "",
            _md_table(
                ["Category", "Issues"],
                [
                    ["Indicator set titles", counts["is_titles"]],
                    ["Finance solutions — type not set", counts["fs_type"]],
                    ["Finance solutions — cross-field violations", counts["fs_cross"]],
                    ["Finance solutions — removed sector values", counts["fs_sector"]],
                    ["Finance solutions — removed SFM values", counts["fs_sfm"]],
                    ["Investment sources — removed investment type", counts["inv_type"]],
                ],
            ),
            "",
            "---",
            "",
        ]

        if total == 0:
            lines.append("## All records conform — Phase 4 is safe to deploy")
            lines.append("")
        else:
            for pname in sorted(per_project):
                pissues = per_project[pname]
                lines.append(f"## {pname}")
                lines.append("")

                if pissues["indicator_sets"]:
                    lines.append("### Indicator sets")
                    lines.append("")
                    lines.append(
                        _md_table(["Title", "Type", "Check", "Action"], pissues["indicator_sets"])
                    )
                    lines.append("")

                if pissues["finance_solutions"]:
                    lines.append("### Finance solutions")
                    lines.append("")
                    lines.append(
                        _md_table(["Name", "Check", "Action"], pissues["finance_solutions"])
                    )
                    lines.append("")

                if pissues["investment_sources"]:
                    lines.append("### Investment sources")
                    lines.append("")
                    lines.append(
                        _md_table(
                            ["Finance solution", "Check", "Action"], pissues["investment_sources"]
                        )
                    )
                    lines.append("")

                lines.append("---")
                lines.append("")

        lines.append("*Run `python manage.py check_gfcr_data` to regenerate.*")
        lines.append("")

        content = "\n".join(lines)

        output_path = options.get("output") or f"gfcr_audit_{today_str}.md"
        with open(output_path, "w") as f:
            f.write(content)

        self.stdout.write(output_path)

    @staticmethod
    def _check_indicator_sets(isets):
        for iset in isets:
            pname = iset.project.name
            title = iset.title
            itype = iset.indicator_set_type
            type_label = "Report" if itype == "report" else "Target"

            if title not in _ALL_VALID_TITLES:
                yield (
                    pname,
                    title,
                    type_label,
                    "IS-1",
                    "Update title to one of the six canonical values",
                    "is_titles",
                )

            if title in _TARGET_TITLES and itype == "report":
                yield (
                    pname,
                    title,
                    type_label,
                    "IS-2",
                    "Update title to a valid report title",
                    "is_titles",
                )
            elif title in _REPORT_TITLES and itype == "target":
                yield (
                    pname,
                    title,
                    type_label,
                    "IS-2",
                    "Update title to a valid target title",
                    "is_titles",
                )

    @staticmethod
    def _check_finance_solutions(finance_solutions, has_type_col, has_geo, has_taf, has_num):
        for fs in finance_solutions:
            pname = fs.indicator_set.project.name
            name = fs.name
            sfm = fs.sustainable_finance_mechanisms or []

            # FS-1 (always run)
            if not has_type_col:
                yield (
                    pname,
                    name,
                    "finance_solutions",
                    "FS-1",
                    "Open the finance solution and assign a type",
                    "fs_type",
                )
                fs_type = None
            else:
                fs_type = getattr(fs, "type", None)
                if fs_type is None:
                    yield (
                        pname,
                        name,
                        "finance_solutions",
                        "FS-1",
                        "Open the finance solution and assign a type",
                        "fs_type",
                    )

            # Cross-field checks — only when type column exists and type is set on this record
            if has_type_col and fs_type is not None:
                if fs_type == "business" and fs.sector == "":
                    yield (
                        pname,
                        name,
                        "finance_solutions",
                        "FS-2",
                        "Set sector (required for Business solution)",
                        "fs_cross",
                    )

                if fs_type != "business" and fs.sector != "":
                    yield (
                        pname,
                        name,
                        "finance_solutions",
                        "FS-3",
                        "Manually clear sector for this finance solution",
                        "fs_cross",
                    )

                if fs_type == "ctf" and has_geo and getattr(fs, "geographical_coverage", "") == "":
                    yield (
                        pname,
                        name,
                        "finance_solutions",
                        "FS-4",
                        "Set geographical_coverage (required for CTF)",
                        "fs_cross",
                    )

                if fs_type != "ctf" and has_geo and getattr(fs, "geographical_coverage", "") != "":
                    yield (
                        pname,
                        name,
                        "finance_solutions",
                        "FS-5",
                        "Manually clear geographical_coverage",
                        "fs_cross",
                    )

                # used_an_incubator: pre-Phase-2 can be None (null=True); post-Phase-2 is "" (null=False, default="").
                # Both "" and None mean "not set" for FS-6 and FS-8.
                used_incubator = fs.used_an_incubator
                if fs_type not in ("business", "financial_mechanism") and used_incubator not in (
                    "",
                    None,
                ):
                    yield (
                        pname,
                        name,
                        "finance_solutions",
                        "FS-6",
                        "Manually clear used_an_incubator",
                        "fs_cross",
                    )

                if (
                    fs_type not in ("business", "financial_mechanism")
                    and has_taf
                    and getattr(fs, "taf_name", "") != ""
                ):
                    yield (
                        pname,
                        name,
                        "finance_solutions",
                        "FS-7",
                        "Manually clear TAF name",
                        "fs_cross",
                    )

                if used_incubator in ("", None) and has_taf and getattr(fs, "taf_name", "") != "":
                    yield (
                        pname,
                        name,
                        "finance_solutions",
                        "FS-8",
                        "Manually clear TAF name, or set used_an_incubator first",
                        "fs_cross",
                    )

                if (
                    fs_type not in ("financial_facility", "business", "financial_mechanism")
                    and fs.local_enterprise
                ):
                    yield (
                        pname,
                        name,
                        "finance_solutions",
                        "FS-9",
                        "Manually uncheck local_enterprise",
                        "fs_cross",
                    )

                if fs_type not in ("business", "financial_mechanism") and fs.gender_smart:
                    yield (
                        pname,
                        name,
                        "finance_solutions",
                        "FS-10",
                        "Manually uncheck gender_smart",
                        "fs_cross",
                    )

                if (
                    fs_type == "taf"
                    and has_num
                    and getattr(fs, "number_of_solutions_supported_by", 0) == 0
                ):
                    yield (
                        pname,
                        name,
                        "finance_solutions",
                        "FS-11",
                        "Set number of solutions supported (required for TAF)",
                        "fs_cross",
                    )

                if (
                    fs_type != "taf"
                    and has_num
                    and getattr(fs, "number_of_solutions_supported_by", 0) != 0
                ):
                    yield (
                        pname,
                        name,
                        "finance_solutions",
                        "FS-12",
                        "Manually set number of solutions supported to 0",
                        "fs_cross",
                    )

                if fs_type != "financial_mechanism" and sfm:
                    yield (
                        pname,
                        name,
                        "finance_solutions",
                        "FS-13",
                        "Manually clear sustainable finance mechanisms",
                        "fs_cross",
                    )

            # Removed-value checks (always run, regardless of whether type is set)
            if fs.sector in _REMOVED_SECTOR_VALUES:
                yield (
                    pname,
                    name,
                    "finance_solutions",
                    "FS-14",
                    f'sector "{fs.sector}" is removed in Phase 4 — change to a valid value',
                    "fs_sector",
                )

            for val in sorted(_REMOVED_SFM_VALUES & set(sfm)):
                yield (
                    pname,
                    name,
                    "finance_solutions",
                    "FS-15",
                    f'"{val}" is removed in Phase 4 — remove or replace',
                    "fs_sfm",
                )

            # INV-1
            for inv in fs.investment_sources.all():
                if inv.investment_type == "public_budget":
                    yield (
                        pname,
                        name,
                        "investment_sources",
                        "INV-1",
                        'Reassign investment_type — "public_budget" is removed in Phase 4',
                        "inv_type",
                    )
