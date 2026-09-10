import logging
import uuid

from django.contrib.gis.db.models.fields import MultiPolygonField, PolygonField
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from ..utils.apikeys import (
    KEY_ID_ISSUE_ATTEMPTS,
    audit_logger,
    generate_api_key,
    log_key_created,
)

logger = logging.getLogger(__name__)

PROPOSED = 10
SUPERUSER_APPROVED = 90
APPROVAL_STATUSES = (
    (SUPERUSER_APPROVED, _("superuser approved")),
    # (50, _('project admin approved')),
    (PROPOSED, _("proposed")),
)


class ExtendedQuerySet(models.QuerySet):
    def get_or_none(self, *args, **kwargs):
        try:
            return super().get(*args, **kwargs)
        except ObjectDoesNotExist:
            return None


class ExtendedManager(models.Manager):
    pass


class ChoicesManager(ExtendedManager):
    def choices(self, order_by, *args, **kwargs):
        return [c.choice for c in super().all().order_by(order_by)]


class Profile(models.Model):
    project_lookup = "projects__project"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_updated_by",
    )
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    picture_url = models.URLField(max_length=2048, blank=True, null=True)
    collect_state = models.JSONField(blank=True, null=True, default=dict)
    explore_state = models.JSONField(blank=True, null=True, default=dict)

    objects = ExtendedManager.from_queryset(ExtendedQuerySet)()

    class Meta:
        db_table = "profile"

    def __str__(self):
        return f"{self.full_name} [{self.pk}]"

    @property
    def full_name(self):  # noqa
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        elif self.num_account_connections == 0:
            return "(pending user)"
        else:
            try:
                return self.email.split("@")[0]
            except IndexError:
                return "N/A"

    @property
    def citation_name(self):  # noqa
        if self.first_name and self.last_name:
            return f"{self.last_name.title()} {self.first_name[:1].title()}"
        elif self.first_name:
            return self.first_name.title()
        elif self.last_name:
            return self.last_name.title()
        else:
            return None

    @property
    def num_account_connections(self):
        return self.authusers.count()


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        "Profile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_created_by",
    )
    updated_on = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        "Profile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_updated_by",
    )

    class Meta:
        abstract = True

    objects = ExtendedManager.from_queryset(ExtendedQuerySet)()


class AreaMixin(models.Model):
    def get_polygon(self):
        for f in self._meta.get_fields():
            if isinstance(f, PolygonField) or isinstance(f, MultiPolygonField):
                return getattr(self, f.attname)  # return poly object, not field
        return None

    @property
    def area(self):
        field = self.get_polygon()
        if field is None:
            return None
        if hasattr(self, "_area"):
            return self._area
        # using a world equal area projection to do the areal measurement; there may be a better one
        # https://epsg.io/3410
        # Thought geography=True would make this unnecessary
        self._area = round(field.transform(3410, clone=True).area / 10000, 3)
        return self._area

    area.fget.short_description = _("area (ha)")

    class Meta:
        abstract = True


class JSONMixin(models.Model):
    data = models.JSONField(null=True, blank=True)

    class Meta:
        abstract = True


class BaseAttributeModel(BaseModel):
    status = models.PositiveSmallIntegerField(
        choices=APPROVAL_STATUSES, default=APPROVAL_STATUSES[-1][0]
    )

    class Meta:
        abstract = True


class BaseChoiceModel(BaseModel):
    @property
    def choice(self):
        ret = {"id": self.pk, "name": self.__str__(), "updated_on": self.updated_on}
        if hasattr(self, "val"):
            ret["val"] = self.val
        return ret

    class Meta:
        abstract = True

    objects = ChoicesManager()


class Country(BaseChoiceModel):
    iso = models.CharField(max_length=2)
    name = models.CharField(max_length=50)

    class Meta:
        db_table = "country"
        verbose_name_plural = "countries"
        ordering = ("name",)

    def __str__(self):
        return _("%s") % self.name


class AuthUser(BaseModel):
    profile = models.ForeignKey(Profile, related_name="authusers", on_delete=models.CASCADE)
    user_id = models.CharField(unique=True, max_length=255)

    class Meta:
        db_table = "authuser"
        # unique=True on user_id is globally unique (stronger than the former unique_together
        # ("profile", "user_id")). No separate UniqueConstraint is needed, but if unique=True
        # is ever relaxed, per-profile uniqueness must be restored explicitly.

    def __str__(self):
        return _("%s") % self.profile.full_name


class Application(BaseModel):
    name = models.CharField(max_length=100)
    profile = models.ForeignKey("Profile", related_name="registered_apps", on_delete=models.CASCADE)
    client_id = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = "applications"
        # unique=True on client_id is globally unique (stronger than the former unique_together
        # ("profile", "client_id")). No separate UniqueConstraint is needed, but if unique=True
        # is ever relaxed, per-profile uniqueness must be restored explicitly.

    def __str__(self):
        return f"{self.profile} - {self.client_id}"


class APIKey(BaseModel):
    """A long-lived credential that acts as its profile.

    The key carries no permissions of its own. Every request it authenticates
    runs as `profile`, with whatever `ProjectProfile.role` that profile holds
    on the project being touched, so a key reaches exactly the data its owner
    reaches and no more - and loses access the moment a membership goes away,
    with no scope list to keep in step.

    The trade is blast radius: a leaked key is the whole of its profile's
    access. Anyone signed in can mint a key for themselves, so the limits are
    on the key rather than on who asks for one: `expires_at` defaults to a year
    rather than to never, revocation is one call, and a key can never mint
    another key. The self-service endpoint adds two ceilings of its own,
    `settings.API_KEY_MAX_LIFETIME_DAYS` and `settings.API_KEY_MAX_PER_PROFILE`,
    so one person cannot accumulate permanent credentials without limit.
    """

    profile = models.ForeignKey("Profile", related_name="api_keys", on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    key_id = models.CharField(max_length=12, unique=True)
    # hex SHA-256 of the secret; the secret itself is never stored
    secret_hash = models.CharField(max_length=64)
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    last_used_ip = models.GenericIPAddressField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "api_key"
        ordering = ("name",)

    def __str__(self):
        # never include secret_hash
        return f"{self.name} [{self.key_id}]"

    @classmethod
    def issue(cls, profile, name, expires_at, actor, replaces=None, created_by=None):
        """Mint a key for `profile` and return ``(key, raw_key)``.

        This is the only place a raw key ever exists, and it exists only in the
        return value: the row keeps the hash, the caller shows the raw key once
        and forgets it. `actor` is who asked for the key, for the audit line.

        A `key_id` collision is astronomically unlikely (12 characters over a
        62-character alphabet), so the retry below is defense in depth against
        an RNG defect rather than an expected event: it means a collision
        costs a second insert instead of surfacing as an opaque 500 to whoever
        is minting the key. Each attempt gets its own savepoint, since an
        IntegrityError would otherwise leave an enclosing transaction unusable.
        """

        for attempt in range(1, KEY_ID_ISSUE_ATTEMPTS + 1):
            key_id, secret_hash, raw = generate_api_key()
            try:
                with transaction.atomic():
                    key = cls.objects.create(
                        profile=profile,
                        name=name,
                        key_id=key_id,
                        secret_hash=secret_hash,
                        expires_at=expires_at,
                        created_by=created_by,
                        updated_by=created_by,
                    )
            except IntegrityError:
                # Only a key_id clash is worth another draw; a bad profile or
                # any other constraint would fail the same way every time.
                is_collision = cls.objects.filter(key_id=key_id).exists()
                if not is_collision or attempt == KEY_ID_ISSUE_ATTEMPTS:
                    raise
                audit_logger.warning(
                    "[apikey.key_id_collision] key_id=%s profile=%s attempt=%s",
                    key_id,
                    profile.pk,
                    attempt,
                )
                continue

            log_key_created(key, actor, replaces=replaces)
            return key, raw

    @classmethod
    def usable_for(cls, profile, now=None):
        """The keys of `profile` that work right now, as a queryset.

        The database-side counterpart of `is_usable`, for the callers that
        have to count or sweep rather than ask about one row: the self-service
        endpoint uses it to hold a profile to `API_KEY_MAX_PER_PROFILE`.
        """

        now = now or timezone.now()
        return cls.objects.filter(profile=profile, is_active=True, revoked_at__isnull=True).filter(
            models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=now)
        )

    @property
    def is_expired(self):
        return self.expires_at is not None and self.expires_at < timezone.now()

    @property
    def is_usable(self):
        return self.is_active and self.revoked_at is None and not self.is_expired

    def revoke(self, reason="", save=True, actor="system"):
        """Retire the key without deleting the row, so the audit trail stays.

        Revocation is one-way and idempotent: re-revoking an already revoked
        key keeps the original timestamp and reason, which is what a reviewer
        asking "when did this stop working" needs.

        `actor` is who took the key away, for the audit line only. It defaults
        to "system" because most revocations come from a signal or the daily
        maintenance command rather than from a person.
        """

        if self.revoked_at is not None:
            return False

        self.revoked_at = timezone.now()
        self.revoked_reason = reason or ""
        self.is_active = False
        if save:
            self.save(update_fields=["revoked_at", "revoked_reason", "is_active", "updated_on"])
        # the counterpart of [apikey.created]. Together they answer "which
        # credentials existed, for whom, and for how long" from the logs alone.
        audit_logger.info(
            "[apikey.revoked] key_id=%s profile=%s actor=%s reason=%s",
            self.key_id,
            self.profile_id,
            actor,
            reason or "unspecified",
        )
        return True
