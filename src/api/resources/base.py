import re
import uuid

from django.contrib.postgres.aggregates import ArrayAgg
from django.utils.translation import gettext_lazy as _
from django.db.models.sql.constants import ORDER_PATTERN
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework import exceptions
from rest_framework.serializers import (
    UUIDField,
    PrimaryKeyRelatedField,
    SerializerMethodField,
)
from rest_framework.exceptions import MethodNotAllowed, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework.fields import empty
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from rest_framework_gis.filterset import GeoFilterSet
from rest_framework_gis.filters import GeometryFilter
from rest_framework_gis.fields import GeometryField
from rest_condition import Or
from django.core.exceptions import FieldDoesNotExist

from django.db.models.fields.related import ForeignObjectRel
from rest_framework.validators import qs_exists
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import (
    Filter,
    BaseInFilter,
    CharFilter,
    FilterSet,
    DateFromToRangeFilter,
    DateTimeFromToRangeFilter,
    RangeFilter,
)
from django_filters.fields import Lookup
from django.conf import settings
from ..models import Tag, APPROVAL_STATUSES
from ..exceptions import check_uuid
from ..permissions import *
from ..utils.auth0utils import get_jwt_token
from ..utils.auth0utils import get_unverified_profile
from .mixins import MethodAuthenticationMixin, UpdatesMixin, OrFilterSetMixin


class ModelNameReadOnlyField(serializers.Field):
    def to_representation(self, obj):
        return u"{}".format(obj.name)


class ModelValReadOnlyField(serializers.Field):
    def to_representation(self, obj):
        return u"{}".format(obj.val)


class TagField(serializers.Field):
    def to_representation(self, obj):
        return u"{}".format(obj.name)

    def to_internal_value(self, data):
        if not isinstance(data, str):
            msg = "Incorrect type. Expected a string, but got %s"
            raise ValidationError(msg % type(data).__name__)
        return Tag(name=data)


class StandardResultPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = "limit"
    max_page_size = 5000


class CurrentProfileDefault:
    requires_context = True

    def __call__(self, serializer_field):
        try:
            token = get_jwt_token(serializer_field.context["request"])
            return get_unverified_profile(token)
        except exceptions.AuthenticationFailed:
            return None

    def __repr__(self):
        return "%s()" % self.__class__.__name__


class BaseAPISerializer(serializers.ModelSerializer):
    id = UUIDField(allow_null=True, default=uuid.uuid4())
    updated_by = PrimaryKeyRelatedField(read_only=True, default=CurrentProfileDefault())

    class Meta:
        available_fields = []
        model = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        request = self.context.get("request")
        if request is None:
            return

        available_fields = getattr(self.Meta, "available_fields", []) or []
        fields = self.get_fields()
        include_fields_param = request.GET.get("include_fields") or ""
        include_fields = [f.strip() for f in include_fields_param.split(",")]
        exclude_fields = []
        if "__all__" in include_fields_param:
            valid_include_fields = available_fields
        else:
            available_field_set = set(available_fields)
            include_field_set = set(include_fields)

            # Only include additional fields that have been asked for.
            valid_include_fields = include_field_set.intersection(available_field_set)
            # Any additional fields that haven't been asked for ensure they
            # are removed from serializer.
            exclude_fields = available_field_set.difference(valid_include_fields)

        for field in valid_include_fields:
            if field not in available_fields:
                continue
            self.fields[field] = fields.get(field)

        for field in exclude_fields:
            if field in fields:
                self.fields.pop(field)

    def save(self, **kwargs):
        request = self.context.get("request")
        if request is None:
            return

        token = get_jwt_token(request)
        kwargs["updated_by"] = get_unverified_profile(token)
        return super().save(**kwargs)


class BaseViewAPISerializer(BaseAPISerializer):
    updated_by = None
    latitude = SerializerMethodField()
    longitude = SerializerMethodField()

    class Meta:
        exclude = ["project_status", "sample_event_notes"]

    def get_latitude(self, obj):
        if obj.location is not None:
            return obj.location.y
        return None

    def get_longitude(self, obj):
        if obj.location is not None:
            return obj.location.x
        return None


class BaseSUViewAPISerializer(BaseViewAPISerializer):
    class Meta(BaseViewAPISerializer.Meta):
        header_order = [
            "latitude",
            "longitude",
            "site_id",
            "site_name",
            "site_notes",
            "project_id",
            "project_name",
            "project_notes",
            "contact_link",
            "tags",
            "country_id",
            "country_name",
            "reef_type",
            "reef_zone",
            "reef_exposure",
            "management_id",
            "management_name",
            "management_name_secondary",
            "management_est_year",
            "management_size",
            "management_parties",
            "management_compliance",
            "management_rules",
            "management_notes",
            "sample_event_id",
            "sample_date",
            "current_name",
            "tide_name",
            "visibility_name",
            "relative_depth",
            "sample_time",
            "sample_unit_ids",
            "sample_unit_notes",
        ]

    def get_observers(self, obj):
        if obj.observers is not None and isinstance(obj.observers, list):
            return ", ".join(o["name"] for o in obj.observers)
        return None


class BaseViewAPIGeoSerializer(GeoFeatureModelSerializer, BaseAPISerializer):
    location = GeometryField(precision=settings.GEO_PRECISION)

    class Meta:
        exclude = ["project_status", "sample_event_notes"]
        geo_field = "location"


class SampleEventExtendedSerializer(BaseAPISerializer):
    _sample_event = None

    def __init__(self, *args, **kwargs):
        if self._sample_event is None:
            raise Exception(
                "SampleEventExtendedSerializer must be given a _sample_event string"
            )

        self.fields["project_name"] = serializers.ReadOnlyField(
            source="{}.site.project.name".format(self._sample_event)
        )
        self.fields["country_name"] = serializers.ReadOnlyField(
            source="{}.site.country.name".format(self._sample_event)
        )
        self.fields["site_name"] = serializers.ReadOnlyField(
            source="{}.site.name".format(self._sample_event)
        )
        self.fields["latitude"] = serializers.SerializerMethodField()
        self.fields["longitude"] = serializers.SerializerMethodField()
        self.fields["exposure_name"] = serializers.ReadOnlyField(
            source="{}.site.exposure.name".format(self._sample_event)
        )
        self.fields["reef_slope_name"] = serializers.ReadOnlyField(
            source="{}.reef_slope.name".format(self._sample_event)
        )
        self.fields["reef_type_name"] = serializers.ReadOnlyField(
            source="{}.site.reef_type.name".format(self._sample_event)
        )
        self.fields["reef_zone_name"] = serializers.ReadOnlyField(
            source="{}.site.reef_zone.name".format(self._sample_event)
        )
        self.fields["sample_date"] = serializers.ReadOnlyField(
            source="{}.sample_date".format(self._sample_event)
        )
        self.fields["sample_time"] = serializers.ReadOnlyField(
            source="{}.sample_time".format(self._sample_event)
        )
        self.fields["tide_name"] = serializers.ReadOnlyField(
            source="{}.tide.name".format(self._sample_event)
        )
        self.fields["visibility_name"] = serializers.ReadOnlyField(
            source="{}.visibility.name".format(self._sample_event)
        )
        self.fields["current_name"] = serializers.ReadOnlyField(
            source="{}.current.name".format(self._sample_event)
        )
        self.fields["depth"] = serializers.ReadOnlyField(
            source="{}.depth".format(self._sample_event)
        )
        self.fields["management_name"] = serializers.ReadOnlyField(
            source="{}.management.name".format(self._sample_event)
        )
        self.fields["management_name_secondary"] = serializers.ReadOnlyField(
            source="{}.management.name_secondary".format(self._sample_event)
        )
        self.fields["management_est_year"] = serializers.ReadOnlyField(
            source="{}.management.est_year".format(self._sample_event)
        )
        self.fields["management_size"] = serializers.ReadOnlyField(
            source="{}.management.size".format(self._sample_event)
        )
        self.fields["management_compliance"] = serializers.ReadOnlyField(
            source="{}.management.compliance.name".format(self._sample_event)
        )
        self.fields["management_parties"] = serializers.SerializerMethodField()
        self.fields["management_rules"] = serializers.SerializerMethodField()
        self.fields["observers"] = serializers.SerializerMethodField()
        self.fields["site_notes"] = serializers.ReadOnlyField(
            source="{}.site.notes".format(self._sample_event)
        )
        self.fields["management_notes"] = serializers.ReadOnlyField(
            source="{}.management.notes".format(self._sample_event)
        )

        super(SampleEventExtendedSerializer, self).__init__(*args, **kwargs)


class ExtendedSerializer(serializers.ModelSerializer):
    def __init__(self, instance=None, data=empty, exclude=[], *args, **kwargs):
        super(ExtendedSerializer, self).__init__(*args, **kwargs)

        for exc in exclude:
            if exc in self.fields:
                del self.fields[exc]


class ListFilter(Filter):
    def filter(self, qs, value):
        if value is None:
            return qs
        value_list = [v.strip() for v in value.split(u",")]
        return super(ListFilter, self).filter(qs, Lookup(value_list, "in"))


# Return objects that actually are null when user asks for them with 'null'
# Note this can't subclass UUIDFilter because of the additional pattern check (?)
class NullableUUIDFilter(CharFilter):
    def filter(self, qs, value):
        if value != settings.API_NULLQUERY:
            if isinstance(value, uuid.UUID):
                return value.hex
            return super(NullableUUIDFilter, self).filter(qs, value)

        qs = self.get_method(qs)(**{"%s__isnull" % self.field_name: True})
        return qs.distinct() if self.distinct else qs


class BaseAPIFilterSet(FilterSet):
    created_on = DateTimeFromToRangeFilter()
    updated_on = DateTimeFromToRangeFilter()
    created_by = NullableUUIDFilter()
    updated_by = NullableUUIDFilter()

    class Meta:
        fields = ["created_on", "updated_on", "created_by", "updated_by"]


class RelatedOrderingFilter(OrderingFilter):
    """
    Extends OrderingFilter to support ordering by fields in related models
    using the Django ORM __ notation
    https://github.com/tomchristie/django-rest-framework/issues/1005
    """

    # ensure unique pagination when not enough ordering fields are specified; requires "id" field
    def get_ordering(self, request, queryset, view):
        ordering = super().get_ordering(request, queryset, view) or []
        if "id" not in ordering:
            ordering.append("id")
        return ordering

    def is_valid_field(self, model, field_name):
        """
        Return true if the field exists within the model (or in the related
        model specified using the Django ORM __ notation)
        """
        components = field_name.split("__", 1)
        try:
            field = model._meta.get_field(components[0])

            # reverse relation
            if isinstance(field, ForeignObjectRel) and len(components) == 2:
                return self.is_valid_field(field.related_model, components[1])

            # foreign key
            if field.related_model and len(components) == 2:
                return self.is_valid_field(field.related_model, components[1])
            return True
        except FieldDoesNotExist:
            return False

    def remove_invalid_fields(self, queryset, fields, view, request):
        valid_fields = [
            item[0]
            for item in self.get_valid_fields(queryset, view, {"request": request})
        ]
        valid_model_fields = [
            term
            for term in fields
            if self.is_valid_field(queryset.model, term.lstrip("-"))
        ]
        valid_fields = set(valid_fields + valid_model_fields)
        return [
            term
            for term in fields
            if term.lstrip("-") in valid_fields and ORDER_PATTERN.match(term)
        ]


class SafeSearchFilter(SearchFilter):

    def _check_search_terms(self, search_fields, search_terms):
        if (
            not search_fields
            or not search_terms
            or "$" not in [sf[0] for sf in search_fields]
        ):
            return

        for search_term in search_terms:
            try:
                re.compile(search_term)
            except re.error:
                raise ValidationError(f"Invalid search term: {search_term}")

    def filter_queryset(self, request, queryset, view):
        search_fields = self.get_search_fields(view, request)
        search_terms = self.get_search_terms(request)
        self._check_search_terms(search_fields, search_terms)

        return super().filter_queryset(request, queryset, view)


class AggregatedViewFilterSet(OrFilterSetMixin, GeoFilterSet):
    site_id = BaseInFilter(method="id_lookup")
    site_name = BaseInFilter(method="char_lookup")
    site_within = GeometryFilter(field_name="location", lookup_expr="within")
    country_id = BaseInFilter(method="id_lookup")
    country_name = BaseInFilter(method="char_lookup")
    tag_id = BaseInFilter(field_name="tags", method="json_id_lookup")
    tag_name = BaseInFilter(field_name="tags", method="json_name_lookup")
    management_id = BaseInFilter(method="id_lookup")
    management_name = BaseInFilter(method="full_management_name")

    class Meta:
        fields = [
            "site_id",
            "site_name",
            "site_within",
            "country_id",
            "country_name",
            "tag_id",
            "tag_name",
            "reef_type",
            "reef_zone",
            "reef_exposure",
            "management_id",
            "management_name",
        ]

    def full_management_name(self, queryset, name, value):
        fields = ["management_name", "management_name_secondary"]
        return self.str_or_lookup(queryset, fields, value, lookup_expr="icontains")


class BaseSEFilterSet(AggregatedViewFilterSet):
    id = BaseInFilter(method="id_lookup")
    sample_event_id = BaseInFilter(method="id_lookup")
    sample_date = DateFromToRangeFilter()
    management_est_year = RangeFilter()
    management_size = RangeFilter()
    management_party = BaseInFilter(
        field_name="management_parties", method="char_lookup"
    )
    management_compliance = BaseInFilter(method="char_lookup")
    management_rule = BaseInFilter(field_name="management_rules", method="char_lookup")
    current_name = BaseInFilter(method="char_lookup")
    tide_name = BaseInFilter(method="char_lookup")
    visibility_name = BaseInFilter(method="char_lookup")

    class Meta:
        fields = [
            "sample_event_id",
            "sample_date",
            "management_est_year",
            "management_size",
            "management_party",
            "management_compliance",
            "management_rule",
            "current_name",
            "tide_name",
            "visibility_name",
        ]


class BaseSUObsFilterSet(BaseSEFilterSet):
    label = BaseInFilter(method="char_lookup")
    depth = RangeFilter()
    relative_depth = BaseInFilter(method="char_lookup")
    observers = BaseInFilter(method="json_name_lookup")

    class Meta:
        fields = [
            "label",
            "depth",
            "relative_depth",
            "observers",
        ]


class BaseApiViewSet(MethodAuthenticationMixin, viewsets.ModelViewSet, UpdatesMixin):
    """
    Include this as mixin to make your ListAPIView paginated & give it the ability to order by field name
    """

    pagination_class = StandardResultPagination

    filter_backends = (DjangoFilterBackend, RelatedOrderingFilter, SafeSearchFilter)

    _serializer_class_for_fields = {}

    lookup_value_regex = r"[0-9a-fA-F]{8}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{12}"

    permission_classes = [DefaultPermission]

    def get_serializer_class_for_fields(self, serializer_class, fields):
        fields = fields.strip().split(",")
        fields.sort()
        fields = tuple(fields)
        if fields in self._serializer_class_for_fields:
            return self._serializer_class_for_fields[fields]

        # Doing this because a simple copy.copy() doesn't work here.
        meta = type("Meta", (serializer_class.Meta, object), {"fields": fields})
        limited_fields_serializer = type(
            "LimitedFieldsSerializer", (serializer_class,), {"Meta": meta}
        )
        self._serializer_class_for_fields[fields] = limited_fields_serializer
        return limited_fields_serializer

    def get_serializer_class(self):
        """
        Allow the `fields` query parameter to limit the returned fields
        in list and detail views.  `fields` takes a comma-separated list of
        fields.
        """
        serializer_class = super(BaseApiViewSet, self).get_serializer_class()
        fields = self.request.query_params.get("fields")
        if self.request.method == "GET" and fields:
            return self.get_serializer_class_for_fields(serializer_class, fields)
        return serializer_class

    def _set_updated_by(self, request):
        token = get_jwt_token(request)
        return get_unverified_profile(token)

    def perform_create(self, serializer):
        updated_by = self._set_updated_by(self.request)
        serializer.save(updated_by=updated_by)

    def perform_update(self, serializer):
        updated_by = self._set_updated_by(self.request)
        serializer.save(updated_by=updated_by)

    def get_object(self):
        pk = check_uuid(self.kwargs.get(self.lookup_field))
        return super(BaseApiViewSet, self).get_object()


class BaseAttributeApiViewSet(BaseApiViewSet):
    permission_classes = [
        Or(UnauthenticatedReadOnlyPermission, AttributeAuthenticatedUserPermission)
    ]

    method_authentication_classes = {"GET": []}

    def perform_create(self, serializer):
        # Here is where we could set status based on user role
        # for now, make it always lowest when set by API, though this is also model default
        serializer.save(status=APPROVAL_STATUSES[-1][0])

    def perform_update(self, serializer):
        serializer.save(status=APPROVAL_STATUSES[-1][0])


class BaseProjectApiViewSet(BaseApiViewSet):
    project_lookup = None

    permission_classes = [
        Or(
            ProjectDataReadOnlyPermission,
            ProjectDataCollectorPermission,
            ProjectDataAdminPermission,
        )
    ]

    def perform_update(self, serializer):
        requested_project = uuid.UUID(check_uuid(self.request.data.get("project")))
        existing_project = self.get_object().project.pk
        if requested_project != existing_project:
            raise ValidationError(
                "Reassigning project data to another project not currently supported."
            )
        serializer.save()

    def limit_to_project(self, request, *args, **kwargs):
        model = self.get_queryset().model
        if hasattr(model, "project_lookup") and model.project_lookup is not None:
            project_filter = {model.project_lookup: check_uuid(kwargs["project_pk"])}
            self.queryset = self.get_queryset().filter(**project_filter)
        return self.queryset

    def list(self, request, *args, **kwargs):
        self.limit_to_project(request, *args, **kwargs)
        return super(BaseProjectApiViewSet, self).list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        self.limit_to_project(request, *args, **kwargs)
        return super(BaseProjectApiViewSet, self).retrieve(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        self.limit_to_project(request, *args, **kwargs)
        return super(BaseProjectApiViewSet, self).create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        self.limit_to_project(request, *args, **kwargs)
        return super(BaseProjectApiViewSet, self).update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        self.limit_to_project(request, *args, **kwargs)
        return super(BaseProjectApiViewSet, self).partial_update(
            request, *args, **kwargs
        )

    def destroy(self, request, *args, **kwargs):
        self.limit_to_project(request, *args, **kwargs)
        return super(BaseProjectApiViewSet, self).destroy(request, *args, **kwargs)

    @action(detail=False, methods=["POST"])
    def missing(self, request, *args, **kwargs):
        self.limit_to_project(request, *args, **kwargs)
        return super(BaseProjectApiViewSet, self).missing(request, *args, **kwargs)


class BaseChoiceApiViewSet(MethodAuthenticationMixin, viewsets.ViewSet):
    permission_classes = [UnauthenticatedReadOnlyPermission]

    method_authentication_classes = {"GET": []}

    # If we need to filter according to project role, we do this here
    def _filter(self, keys=None):
        choices = []
        model_choices = self.get_choices()
        for key, chc in model_choices.items():
            if keys is not None and key not in keys:
                continue
            choices.append({"name": key, "data": chc["data"]})
        return choices

    def list(self, request):
        choices = self._filter()
        return Response(choices)

    def retrieve(self, request, pk=None):
        choices = self._filter(keys=[pk])
        try:
            return Response(choices[0])
        except IndexError:
            raise NotFound("{} choice not found.".format(pk))

    def create(self, request):
        raise MethodNotAllowed("POST")

    def update(self, request, pk=None):
        raise MethodNotAllowed("PUT")

    def partial_update(self, request, pk=None):
        raise MethodNotAllowed("PATCH")

    def destroy(self, request, pk=None):
        raise MethodNotAllowed("DELETE")


class ArrayAggExt(ArrayAgg):
    template = "ARRAY_REMOVE(%(function)s(%(distinct)s%(expressions)s %(ordering)s), NULL)"


class RegionsSerializerMixin():
    """
    Assumes that the viewset queryset is using
    `.annotate(regions_=ArrayAgg("regions"))`
    """
    def to_representation(self, instance):
        if hasattr(instance, "regions_"):
            self.fields["regions"] = serializers.ListField(source="regions_")
        return super().to_representation(instance)
