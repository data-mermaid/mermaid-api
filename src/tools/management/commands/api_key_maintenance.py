"""C4: daily upkeep for API keys.

Two jobs, neither of which the auth backend can do on its own:

- Deactivate keys whose `expires_at` has passed. The backend already rejects
  them, but the row still says `is_active=True`, so the admin list lies about
  which credentials are live.
- Report long-lived keys that nobody has used for a long time. These are the
  credentials that get forgotten. "Long-lived" is no expiry at all, or an
  expiry further out than `settings.API_KEY_MAX_LIFETIME_DAYS`, which is a
  permanent key wearing a date. Nothing is revoked automatically; a quiet key
  may just be a quarterly job.
"""

from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from api.models import APIKey
from api.utils.apikeys import audit_logger

STALE_DAYS = 180


class Command(BaseCommand):
    help = (
        "Deactivate expired API keys and report long-lived keys that have gone "
        "unused. Use --dry-run to report without writing."
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
            help=f"Days of disuse before a long-lived key is reported (default {STALE_DAYS}).",
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
            audit_logger.info(
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
        # An expiry past the ceiling the API will issue is a no-expiry key that
        # went in through another door (the admin, a fixture, an older row), so
        # it belongs in the same report rather than outside it.
        horizon = now + timedelta(days=settings.API_KEY_MAX_LIFETIME_DAYS)
        stale = (
            APIKey.objects.filter(is_active=True, revoked_at__isnull=True)
            .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=horizon))
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
            expires = key.expires_at.isoformat() if key.expires_at else "never"
            last_used = key.last_used_at.isoformat() if key.last_used_at else "never"
            audit_logger.info(
                "[apikey.stale] key_id=%s profile=%s last_used_at=%s expires_at=%s",
                key.key_id,
                key.profile_id,
                last_used,
                expires,
            )
            self.stdout.write(
                f"  stale: key_id={key.key_id} profile_id={key.profile_id} "
                f"last_used={last_used} expires={expires}"
            )

        self.stdout.write(
            f"api_key_maintenance: {count} long-lived key(s) unused for {stale_days} days"
        )
