import re
from collections import defaultdict
from functools import cache
from typing import NamedTuple

import django_filters
from django.contrib.postgres.aggregates import StringAgg
from django.db.models import Case, CharField, Q, Value, When
from django.db.models.functions import Cast, Concat
from rest_framework import exceptions, serializers

from ...exceptions import check_uuid
from ...models import Observer, SampleEvent, TransectMethod
from ...utils import get_subclasses
from ..base import BaseAPIFilterSet, BaseAPISerializer, BaseProjectApiViewSet


class MethodInfo(NamedTuple):
    name: str  # relation name from TransectMethod, e.g. "beltfish"
    sample_unit: str  # path to the sample unit, e.g. "beltfish__transect"
    sample_unit_fields: frozenset
    protocol: str


@cache
def sample_unit_methods():
    """One entry per TransectMethod subclass, so every protocol is covered without
    listing them here."""
    methods = []
    for method_cls in get_subclasses(TransectMethod):
        name = method_cls._meta.model_name
        su_field = method_cls.sample_unit_field()
        su_model = method_cls._meta.get_field(su_field).related_model
        su_fields = frozenset(f.name for f in su_model._meta.get_fields())
        methods.append(MethodInfo(name, f"{name}__{su_field}", su_fields, method_cls.protocol))
    return methods


def _sample_unit_field_case(field):
    """The sample unit's `field` (e.g. "depth", "sample_event__site__name"), whichever
    protocol the method is."""
    return Case(
        *[
            When(**{f"{m.sample_unit}__{field}__isnull": False}, then=f"{m.sample_unit}__{field}")
            for m in sample_unit_methods()
            if field.split("__")[0] in m.sample_unit_fields
        ]
    )


def _size_display(m):
    length = Cast(f"{m.sample_unit}__len_surveyed", CharField())
    if "width" in m.sample_unit_fields:
        width = Cast(f"{m.sample_unit}__width__name", CharField())
        return Concat(length, Value("m x "), width)
    if "len_surveyed" in m.sample_unit_fields:
        return Concat(length, Value("m"))
    return Concat(Cast(f"{m.sample_unit}__quadrat_size", CharField()), Value("m"))


class ListFilter(django_filters.Filter):
    def filter(self, qs, value):
        value = value or ""
        values = [v.strip() for v in value.split(",")]
        if values:
            qry_args = {f"{self.field_name}__in": values}
            qs = qs.filter(**qry_args)
        return qs


class SearchNonFieldFilter(django_filters.Filter):
    SEARCH_FIELDS = [
        "protocol_name",
        "site_name",
        "management_name",
        "observers__profile__first_name",
        "observers__profile__last_name",
    ]

    def filter(self, qs, value):
        value = value or ""

        try:
            re.compile(value)
        except re.error:
            raise exceptions.ValidationError("Invalid search")

        qry = Q()
        for field in self.SEARCH_FIELDS:
            qry |= Q(**{f"{field}__iregex": value})
        return qs.filter(qry).distinct()


class SampleUnitMethodFilterSet(BaseAPIFilterSet):
    protocol = ListFilter(field_name="protocol_name")
    search = SearchNonFieldFilter()

    class Meta:
        model = TransectMethod
        fields = ["protocol", "search"]


class SampleUnitMethodSerializer(BaseAPISerializer):
    protocol = serializers.SerializerMethodField()
    sample_event = serializers.SerializerMethodField()
    site_name = serializers.ReadOnlyField()
    site = serializers.SerializerMethodField()
    management_name = serializers.ReadOnlyField()
    management = serializers.SerializerMethodField()
    depth = serializers.SerializerMethodField(method_name="get_sample_unit_depth")
    sample_date = serializers.SerializerMethodField()
    sample_unit_number = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()
    size = serializers.SerializerMethodField()
    size_display = serializers.ReadOnlyField()
    observers = serializers.SerializerMethodField()

    def get_protocol(self, o):
        return o.protocol

    def _get_sample_event(self, o):
        se = self.context["sample_events"].get(str(o.sample_unit.sample_event_id))
        return se

    def get_sample_event(self, o):
        se = self._get_sample_event(o)
        return str(se.pk) if se else None

    def get_sample_unit_number(self, o):
        sample_unit = o.sample_unit
        if hasattr(sample_unit, "number"):
            return sample_unit.number
        return None

    def get_site(self, o):
        se = self._get_sample_event(o)
        if se is None:
            return
        return se.site_id

    def get_management(self, o):
        se = self._get_sample_event(o)
        if se is None:
            return
        return se.management_id

    def get_sample_date(self, o):
        se = self._get_sample_event(o)
        if se is None:
            return
        return se.sample_date

    def get_size(self, o):
        # same precedence as size_display
        sample_unit = o.sample_unit
        if hasattr(sample_unit, "width_id"):
            return dict(
                width=sample_unit.width_id,
                width_units="m",
                len_surveyed=sample_unit.len_surveyed,
                len_surveyed_units="m",
            )
        if hasattr(sample_unit, "len_surveyed"):
            return dict(len_surveyed=sample_unit.len_surveyed, len_surveyed_units="m")
        if hasattr(sample_unit, "quadrat_size"):
            return dict(quadrat_size=sample_unit.quadrat_size, quadrat_size_units="m")
        return None

    def get_label(self, o):
        return o.sample_unit.label if hasattr(o.sample_unit, "label") else ""

    def get_observers(self, o):
        context = self.context
        return context["observers"].get(str(o.id))

    def get_sample_unit_depth(self, o):
        return o.sample_unit_method_depth

    class Meta:
        model = TransectMethod
        exclude = []


class SampleUnitMethodView(BaseProjectApiViewSet):
    queryset = TransectMethod.objects.all()

    filterset_class = SampleUnitMethodFilterSet
    serializer_class = SampleUnitMethodSerializer
    http_method_names = ["get", "head"]
    ordering = ("id",)
    _project_transect_method_ids = []

    ordering_fields = (
        "management_name",
        "site_name",
        "protocol_name",
        "sample_unit_number",
        "sample_unit_method_depth",
        "sample_date",
        "size_display",
        "observers_display",
    )

    def get_queryset(self):
        methods = sample_unit_methods()
        qs = self.queryset.select_related(
            *[m.name for m in methods], *[m.sample_unit for m in methods]
        )

        protocol_condition = Case(
            *[When(**{f"{m.name}__id__isnull": False}, then=Value(m.protocol)) for m in methods],
            output_field=CharField(),
        )
        size_condition = Case(
            *[When(**{f"{m.name}__id__isnull": False}, then=_size_display(m)) for m in methods]
        )
        observers = StringAgg(
            Concat(
                Cast("observers__profile__first_name", CharField()),
                Value(" "),
                Cast("observers__profile__last_name", CharField()),
            ),
            delimiter=", ",
            distinct=True,
        )

        return qs.annotate(
            protocol_name=protocol_condition,
            site_name=_sample_unit_field_case("sample_event__site__name"),
            management_name=_sample_unit_field_case("sample_event__management__name"),
            sample_unit_number=_sample_unit_field_case("number"),
            sample_unit_method_depth=_sample_unit_field_case("depth"),
            sample_date=_sample_unit_field_case("sample_event__sample_date"),
            size_display=size_condition,
            observers_display=observers,
        )

    def limit_to_project(self, request, *args, **kwargs):
        prj_pk = check_uuid(kwargs["project_pk"])
        self._project_transect_method_ids = list(TransectMethod.project_method_ids(prj_pk))
        self.queryset = self.get_queryset().filter(id__in=self._project_transect_method_ids)
        return self.queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        transect_method_ids = self._project_transect_method_ids

        sample_event_ids = (
            TransectMethod.objects.filter(id__in=transect_method_ids)
            .annotate(_se_id=_sample_unit_field_case("sample_event__id"))
            .values_list("_se_id", flat=True)
        )

        context["sample_events"] = {
            str(se.id): se
            for se in SampleEvent.objects.select_related("site", "management").filter(
                id__in={se_id for se_id in sample_event_ids if se_id is not None}
            )
        }

        observers = Observer.objects.select_related("profile").filter(
            transectmethod_id__in=transect_method_ids
        )
        observer_lookup = defaultdict(list)
        # profile_name can COUNT the profile's authusers (nameless profiles); once per profile
        names = {}
        for obs in observers:
            if obs.profile_id not in names:
                names[obs.profile_id] = obs.profile_name
            observer_lookup[str(obs.transectmethod_id)].append(names[obs.profile_id])
        for transect_method_id, observers in observer_lookup.items():
            observer_lookup[transect_method_id] = sorted(observers)

        context["observers"] = observer_lookup
        return context

    def retrieve(self, request, pk=None, **kwargs):
        # Disable the detail fetch - the method-specific endpoints
        # should be used for SampleUnitMethod details
        raise exceptions.NotFound(code=404)
