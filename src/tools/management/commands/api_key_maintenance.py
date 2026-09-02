"""C4: daily upkeep for API keys.

Two jobs, neither of which the auth backend can do on its own:

- Deactivate keys whose `expires_at` has passed. The backend already rejects
  them, but the row still says `is_active=True`, so the admin list lies about
  which credentials are live.
- Report keys with no expiry that nobody has used for a long time. These are
  the credentials that get forgotten. Nothing is revoked automatically; a
  quiet key may just be a quarterly job.
"""

import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from api.models import APIKey

logger = logging.getLogger(__name__)

STALE_DAYS = 180


class Command(BaseCommand):
    help = (
        "Deactivate expired API keys and report never-expiring keys that have "
        "gone unused. Use --dry-run to report without writing."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would change without deactivating anything.",
        )
        parser.add_argument(
            "--stale-days",
            type=int,
            default=STALE_DAYS,
            help=f"Days of disuse before a no-expiry key is reported (default {STALE_DAYS}).",
        )

    def handle(self, *args, **options):
        now = timezone.now()
        self._deactivate_expired(now, options["dry_run"])
        self._report_stale(now, options["stale_days"])

    def _deactivate_expired(self, now, dry_run):
        expired = APIKey.objects.filter(
            is_active=True, expires_at__isnull=False, expires_at__lt=now
        )

        count = 0
        for key in expired:
            count += 1
            # Expired is not revoked: revoked_at stays null so a reviewer can
            # still tell a key that ran out from one somebody took away.
            logger.info(
                "[apikey.expired] key_id=%s profile=%s expires_at=%s",
                key.key_id,
                key.profile_id,
                key.expires_at.isoformat(),
            )
            self.stdout.write(f"  expired: {key} (expired {key.expires_at.isoformat()})")

        if count and not dry_run:
            # One UPDATE rather than a save() per row: nothing here needs the
            # pre_save hooks, and an expiry sweep can touch many rows at once.
            APIKey.objects.filter(
                is_active=True, expires_at__isnull=False, expires_at__lt=now
            ).update(is_active=False, updated_on=now)

        verb = "would deactivate" if dry_run else "deactivated"
        self.stdout.write(f"api_key_maintenance: {verb} {count} expired key(s)")

    def _report_stale(self, now, stale_days):
        cutoff = now - timedelta(days=stale_days)
        stale = (
            APIKey.objects.filter(is_active=True, expires_at__isnull=True, revoked_at__isnull=True)
            .filter(
                # Never used and issued long ago counts as stale too, otherwise
                # a key that was never wired up would never be reported.
                Q(last_used_at__lt=cutoff) | Q(last_used_at__isnull=True, created_on__lt=cutoff)
            )
            .select_related("profile")
        )

        count = 0
        for key in stale:
            count += 1
            logger.info(
                "[apikey.stale] key_id=%s profile=%s last_used_at=%s",
                key.key_id,
                key.profile_id,
                key.last_used_at.isoformat() if key.last_used_at else "never",
            )
            self.stdout.write(
                f"  stale: {key} profile={key.profile.email} "
                f"last_used={key.last_used_at.isoformat() if key.last_used_at else 'never'}"
            )

        self.stdout.write(
            f"api_key_maintenance: {count} no-expiry key(s) unused for {stale_days} days"
        )
