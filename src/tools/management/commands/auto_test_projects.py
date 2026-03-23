import csv
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Exists, OuterRef
from django.utils import timezone

from api.models import GFCRIndicatorSet, Project, SampleEvent

APP_ROOT = Path(settings.BASE_DIR)

INACTIVITY_THRESHOLD_DAYS = 365


class Command(BaseCommand):
    help = (
        "Set status=TEST for projects inactive >1yr with no submitted SUs and no GFCR data. "
        "Use --dry-run to preview as CSV without making changes."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help=(
                "Output a CSV of projects that would be marked TEST, plus a second section "
                "of projects with 0 submitted SUs that don't meet the other criteria."
            ),
        )
        parser.add_argument(
            "--require-updated-by",
            action="store_true",
            help="Only include projects where updated_by is not null.",
        )

    def _build_querysets(self, require_updated_by, one_year_ago):
        has_sample_events = Exists(SampleEvent.objects.filter(site__project=OuterRef("pk")))
        has_gfcr = Exists(GFCRIndicatorSet.objects.filter(project=OuterRef("pk")))

        zero_su_projects = Project.objects.annotate(
            has_submitted_sus=has_sample_events,
            has_gfcr_data=has_gfcr,
        ).filter(has_submitted_sus=False)

        candidates = (
            zero_su_projects.filter(
                updated_on__lt=one_year_ago,
                is_demo=False,
                has_gfcr_data=False,
            )
            .exclude(status=Project.TEST)
            .exclude(id=settings.DEMO_PROJECT_ID)
        )

        if require_updated_by:
            candidates = candidates.filter(updated_by__isnull=False)

        return zero_su_projects, candidates

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        require_updated_by = options["require_updated_by"]
        one_year_ago = timezone.now() - timedelta(days=INACTIVITY_THRESHOLD_DAYS)

        zero_su_projects, candidates = self._build_querysets(require_updated_by, one_year_ago)
        candidate_ids = list(candidates.values_list("id", flat=True))
        count = len(candidate_ids)

        if dry_run:
            self._output_csv(
                candidates, zero_su_projects, candidate_ids, one_year_ago, require_updated_by
            )
            return

        if count == 0:
            self.stdout.write("No projects to update.")
            return

        self.stdout.write(f"Setting {count} project(s) to TEST status:")
        for p in candidates.select_related("updated_by").order_by("name"):
            self.stdout.write(
                f"  - {p.name} (id={p.id}, "
                f"last_updated={p.updated_on.date()}, "
                f"status={p.get_status_display()})"
            )
        Project.objects.filter(id__in=candidate_ids).update(status=Project.TEST)
        self.stdout.write("Done.")

    def _output_csv(
        self, candidates, zero_su_projects, candidate_ids, one_year_ago, require_updated_by
    ):
        candidates_path = APP_ROOT / "auto_test_projects_candidates.csv"
        excluded_path = APP_ROOT / "auto_test_projects_excluded.csv"

        # File 1: projects that will be marked TEST
        with open(candidates_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["project_id", "project_name", "current_status", "updated_on", "updated_by_email"]
            )
            for p in candidates.select_related("updated_by").order_by("name"):
                writer.writerow(
                    [
                        str(p.id),
                        p.name,
                        p.get_status_display(),
                        p.updated_on.date(),
                        p.updated_by.email if p.updated_by else "",
                    ]
                )
        self.stdout.write(f"Candidates written to {candidates_path}")

        # File 2: zero-SU projects that don't qualify (excluding already-TEST)
        excluded = (
            zero_su_projects.exclude(id__in=candidate_ids)
            .exclude(status=Project.TEST)
            .select_related("updated_by")
            .order_by("name")
        )

        reason_headers = [
            "reason_is_demo",
            "reason_has_gfcr",
            "reason_too_recent",
            "reason_is_demo_template",
        ]
        if require_updated_by:
            reason_headers.append("reason_missing_updated_by")

        demo_project_id = str(settings.DEMO_PROJECT_ID)
        with open(excluded_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "project_id",
                    "project_name",
                    "current_status",
                    "updated_on",
                    "updated_by_email",
                ]
                + reason_headers
            )
            for p in excluded:
                row = [
                    str(p.id),
                    p.name,
                    p.get_status_display(),
                    p.updated_on.date(),
                    p.updated_by.email if p.updated_by else "",
                    p.is_demo,
                    p.has_gfcr_data,
                    p.updated_on >= one_year_ago,
                    str(p.id) == demo_project_id,
                ]
                if require_updated_by:
                    row.append(p.updated_by is None)
                writer.writerow(row)
        self.stdout.write(f"Excluded written to {excluded_path}")
