import uuid

from django.contrib.gis.db.models.fields import MultiPolygonField, PolygonField
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils.translation import gettext_lazy as _

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
    app_settings = models.JSONField(blank=True, default=dict)

    objects = ExtendedManager.from_queryset(ExtendedQuerySet)()

    class Meta:
        db_table = "profile"

    def __str__(self):
        return "{} [{}]".format(self.full_name, self.pk)

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
        unique_together = (
            "profile",
            "user_id",
        )

    def __str__(self):
        return _("%s") % self.profile.full_name


class Application(BaseModel):
    name = models.CharField(max_length=100)
    profile = models.ForeignKey("Profile", related_name="registered_apps", on_delete=models.CASCADE)
    client_id = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = "applications"
        unique_together = ("profile", "client_id")

    def __str__(self):
        return "{} - {}".format(self.profile, self.client_id)
