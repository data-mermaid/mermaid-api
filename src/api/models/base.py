import uuid

from django.db import models
from django.contrib.postgres.fields import JSONField
from django.contrib.gis.db.models.fields import PolygonField, MultiPolygonField
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ObjectDoesNotExist

PROPOSED = 10
SUPERUSER_APPROVED = 90
APPROVAL_STATUSES = (
    (SUPERUSER_APPROVED, _(u'superuser approved')),
    # (50, _(u'project admin approved')),
    (PROPOSED, _(u'proposed')),
)


class ExtendedManager(models.Manager):

    def get_or_none(self, *args, **kwargs):
        try:
            return super().get(*args, **kwargs)
        except ObjectDoesNotExist:
            return None


class ChoicesManager(ExtendedManager):

    def choices(self, order_by, *args, **kwargs):
        return [c.choice for c in super().all().order_by(order_by)]


class Profile(models.Model):
    project_lookup = 'projects__project'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey('self', on_delete=models.SET_NULL,
                                   null=True, blank=True,
                                   related_name='%(class)s_updated_by')
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)

    objects = ExtendedManager()

    class Meta:
        db_table = 'profile'

    def __str__(self):
        return u'{} [{}]'.format(self.full_name, self.pk)

    @property
    def full_name(self):
        name = []
        if self.first_name:
            name.append(self.first_name)

        if self.last_name:
            name.append(self.last_name)

        if len(name) > 0:
            return ' '.join(name)
        else:
            try:
                email_name = self.email.split('@')[0]
                return email_name
            except IndexError:
                return ''


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('Profile', on_delete=models.SET_NULL,
                                   null=True, blank=True,
                                   related_name='%(class)s_created_by')
    updated_on = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey('Profile', on_delete=models.SET_NULL,
                                   null=True, blank=True,
                                   related_name='%(class)s_updated_by')

    class Meta:
        abstract = True

    objects = ExtendedManager()


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
        if hasattr(self, '_area'):
            return self._area
        # using a world equal area projection to do the areal measurement; there may be a better one
        # https://epsg.io/3410
        # Thought geography=True would make this unnecessary
        self._area = round(field.transform(3410, clone=True).area / 10000, 3)
        return self._area
    area.fget.short_description = _(u'area (ha)')

    class Meta:
        abstract = True


class JSONMixin(models.Model):
    data = JSONField(null=True, blank=True)

    class Meta:
        abstract = True


class BaseAttributeModel(BaseModel):
    status = models.PositiveSmallIntegerField(choices=APPROVAL_STATUSES, default=APPROVAL_STATUSES[-1][0])

    class Meta:
        abstract = True


class BaseChoiceModel(BaseModel):
    @property
    def choice(self):
        ret = {'id': self.pk, 'name': self.__str__(), 'updated_on': self.updated_on}
        if hasattr(self, 'val'):
            ret['val'] = self.val
        return ret

    class Meta:
        abstract = True

    objects = ChoicesManager()


class Country(BaseChoiceModel):
    iso = models.CharField(max_length=2)
    name = models.CharField(max_length=50)

    class Meta:
        db_table = 'country'
        verbose_name_plural = u'countries'
        ordering = ('name',)

    def __str__(self):
        return _(u'%s') % self.name


class AuthUser(BaseModel):
    profile = models.ForeignKey(Profile, related_name='authusers', on_delete=models.CASCADE)
    user_id = models.CharField(unique=True, max_length=255)

    class Meta:
        db_table = 'authuser'
        unique_together = ('profile', 'user_id',)

    def __str__(self):
        return _(u'%s') % self.profile.full_name


class Application(BaseModel):
    name = models.CharField(max_length=100)
    profile = models.ForeignKey('Profile', related_name='registered_apps',
                                on_delete=models.CASCADE)
    client_id = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = 'applications'
        unique_together = ('profile', 'client_id')

    def __str__(self):
        return '{} - {}'.format(self.profile, self.client_id)


class AppVersion(models.Model):
    application = models.CharField(unique=True, max_length=25)
    version = models.CharField(max_length=25)
