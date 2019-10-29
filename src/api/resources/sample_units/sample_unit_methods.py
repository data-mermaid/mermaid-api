from collections import defaultdict

import re
import django_filters
from django.db.models import Case, CharField, Q, Value, When, CharField
from django.db.models.functions import Concat, Cast
from django_filters import rest_framework as filters
from rest_framework import serializers
from rest_framework import exceptions

from ...exceptions import check_uuid
from ...models import mermaid
from ...models.mermaid import TransectMethod
from ..base import (
    BaseAPIFilterSet,
    BaseAPISerializer,
    BaseProjectApiViewSet,
)


class ListFilter(django_filters.Filter):
    def filter(self, qs, value):
        value = value or ""
        values = [v.strip() for v in value.split(",")]
        if values:
            qry_args = {"{}__in".format(self.field_name): values}
            qs = qs.filter(**qry_args)
        return qs


class SearchNonFieldFilter(django_filters.Filter):
    SEARCH_FIELDS = [
        "protocol_name",
        "site_name",
        "management_name",
        "benthiclit__observers__profile__first_name",
        "benthiclit__observers__profile__last_name",
        "benthicpit__observers__profile__first_name",
        "benthicpit__observers__profile__last_name",
        "beltfish__observers__profile__first_name",
        "beltfish__observers__profile__last_name",
        "habitatcomplexity__observers__profile__first_name",
        "habitatcomplexity__observers__profile__last_name",
        "bleachingquadratcollection__observers__profile__first_name",
        "bleachingquadratcollection__observers__profile__last_name",
    ]

    def filter(self, qs, value):
        value = value or ""
        params = value.replace(",", " ").split()
        qry = Q()
        for field in self.SEARCH_FIELDS:
            for param in params:
                param = re.escape(param).replace(r"\.", ".").replace(r"\*", "*")
                qry |= Q(**{"{}__iregex".format(field): param})
        return qs.filter(qry).distinct()


class SampleUnitMethodFilterSet(BaseAPIFilterSet):
    protocol = ListFilter(field_name="protocol_name")
    search = SearchNonFieldFilter()

    class Meta:
        model = TransectMethod
        fields = ["protocol", "search"]


class SampleUnitMethodSerializer(BaseAPISerializer):
    protocol = serializers.SerializerMethodField()
    site_name = serializers.ReadOnlyField()
    site = serializers.SerializerMethodField()
    management_name = serializers.ReadOnlyField()
    management = serializers.SerializerMethodField()
    depth = serializers.ReadOnlyField()
    sample_date = serializers.SerializerMethodField()
    sample_unit_number = serializers.SerializerMethodField()
    size = serializers.SerializerMethodField()
    size_display = serializers.ReadOnlyField()
    observers = serializers.SerializerMethodField()

    def get_protocol(self, o):
        return o.protocol

    def get_sample_unit_number(self, o):
        sample_unit = o.sample_unit
        if hasattr(sample_unit, "number"):
            return sample_unit.number
        return None

    def get_site(self, o):
        sample_unit = o.sample_unit
        return sample_unit.sample_event.site.id

    def get_management(self, o):
        sample_unit = o.sample_unit
        return sample_unit.sample_event.management.id

    def get_sample_date(self, o):
        sample_unit = o.sample_unit
        return sample_unit.sample_event.sample_date

    def get_size(self, o):
        protocol = o.protocol
        if protocol == mermaid.FISHBELT_PROTOCOL:
            sample_unit = o.sample_unit
            return dict(
                width=sample_unit.width.val,
                width_units="m",
                len_surveyed=sample_unit.len_surveyed,
                len_surveyed_units="m",
            )
        elif protocol in (
            mermaid.BENTHICLIT_PROTOCOL,
            mermaid.BENTHICPIT_PROTOCOL,
            mermaid.HABITATCOMPLEXITY_PROTOCOL,
        ):
            sample_unit = o.sample_unit
            return dict(len_surveyed=sample_unit.len_surveyed, len_surveyed_units="m")
        elif protocol == mermaid.BLEACHINGQC_PROTOCOL:
            sample_unit = o.sample_unit
            return dict(quadrat_size=sample_unit.quadrat_size, quadrat_size_units="m")
        return None

    def get_observers(self, o):
        context = self.context
        return context["observers"].get(str(o.id))

    class Meta:
        model = TransectMethod
        exclude = []


class SampleUnitMethodView(BaseProjectApiViewSet):
    queryset = (
        TransectMethod.objects.select_related(
            "benthiclit",
            "benthicpit",
            "habitatcomplexity",
            "beltfish",
            "bleachingquadratcollection",
        )
        .all()
        .order_by("id")
    )

    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = SampleUnitMethodFilterSet
    serializer_class = SampleUnitMethodSerializer
    http_method_names = ["get", "head"]

    ordering_fields = (
        "management_name",
        "site_name",
        "protocol_name",
        "sample_unit_number",
        "depth",
        "sample_date",
        "size_display",
    )

    def get_queryset(self):
        qs = self.queryset

        protocol_condition = Case(
            When(benthiclit__id__isnull=False, then=Value(mermaid.BENTHICLIT_PROTOCOL)),
            When(benthicpit__id__isnull=False, then=Value(mermaid.BENTHICPIT_PROTOCOL)),
            When(
                habitatcomplexity__id__isnull=False,
                then=Value(mermaid.HABITATCOMPLEXITY_PROTOCOL),
            ),
            When(
                bleachingquadratcollection__id__isnull=False,
                then=Value(mermaid.BLEACHINGQC_PROTOCOL),
            ),
            When(beltfish__id__isnull=False, then=Value(mermaid.FISHBELT_PROTOCOL)),
            output_field=CharField(),
        )

        site_name_condition = Case(
            When(
                benthiclit__transect__sample_event__site__name__isnull=False,
                then="benthiclit__transect__sample_event__site__name",
            ),
            When(
                benthicpit__transect__sample_event__site__name__isnull=False,
                then="benthicpit__transect__sample_event__site__name",
            ),
            When(
                habitatcomplexity__transect__sample_event__site__name__isnull=False,
                then="habitatcomplexity__transect__sample_event__site__name",
            ),
            When(
                bleachingquadratcollection__quadrat__sample_event__site__name__isnull=False,
                then="bleachingquadratcollection__quadrat__sample_event__site__name",
            ),
            When(
                beltfish__transect__sample_event__site__name__isnull=False,
                then="beltfish__transect__sample_event__site__name",
            ),
        )

        management_name_condition = Case(
            When(
                benthiclit__transect__sample_event__management__name__isnull=False,
                then="benthiclit__transect__sample_event__management__name",
            ),
            When(
                benthicpit__transect__sample_event__management__name__isnull=False,
                then="benthicpit__transect__sample_event__management__name",
            ),
            When(
                habitatcomplexity__transect__sample_event__management__name__isnull=False,
                then="habitatcomplexity__transect__sample_event__management__name",
            ),
            When(
                bleachingquadratcollection__quadrat__sample_event__management__name__isnull=False,
                then="bleachingquadratcollection__quadrat__sample_event__management__name",
            ),
            When(
                beltfish__transect__sample_event__management__name__isnull=False,
                then="beltfish__transect__sample_event__management__name",
            ),
        )

        sample_unit_number_condition = Case(
            When(
                benthiclit__transect__number__isnull=False,
                then="benthiclit__transect__number",
            ),
            When(
                benthicpit__transect__number__isnull=False,
                then="benthicpit__transect__number",
            ),
            When(
                habitatcomplexity__transect__number__isnull=False,
                then="habitatcomplexity__transect__number",
            ),
            When(
                beltfish__transect__number__isnull=False,
                then="beltfish__transect__number",
            ),
        )

        depth_condition = Case(
            When(
                benthiclit__transect__sample_event__depth__isnull=False,
                then="benthiclit__transect__sample_event__depth",
            ),
            When(
                benthicpit__transect__sample_event__depth__isnull=False,
                then="benthicpit__transect__sample_event__depth",
            ),
            When(
                habitatcomplexity__transect__sample_event__depth__isnull=False,
                then="habitatcomplexity__transect__sample_event__depth",
            ),
            When(
                bleachingquadratcollection__quadrat__sample_event__depth__isnull=False,
                then="bleachingquadratcollection__quadrat__sample_event__depth",
            ),
            When(
                beltfish__transect__sample_event__depth__isnull=False,
                then="beltfish__transect__sample_event__depth",
            ),
        )

        sample_date_condition = Case(
            When(
                benthiclit__transect__sample_event__sample_date__isnull=False,
                then="benthiclit__transect__sample_event__sample_date",
            ),
            When(
                benthicpit__transect__sample_event__sample_date__isnull=False,
                then="benthicpit__transect__sample_event__sample_date",
            ),
            When(
                habitatcomplexity__transect__sample_event__sample_date__isnull=False,
                then="habitatcomplexity__transect__sample_event__sample_date",
            ),
            When(
                bleachingquadratcollection__quadrat__sample_event__sample_date__isnull=False,
                then="bleachingquadratcollection__quadrat__sample_event__sample_date",
            ),
            When(
                beltfish__transect__sample_event__sample_date__isnull=False,
                then="beltfish__transect__sample_event__sample_date",
            ),
        )

        size_condition = Case(
            When(
                benthiclit__id__isnull=False,
                then=Concat(Cast("benthiclit__transect__len_surveyed", CharField()), Value("m"))
            ),
            When(
                benthicpit__id__isnull=False,
                then=Concat(Cast("benthicpit__transect__len_surveyed", CharField()), Value("m"))
            ),
            When(
                habitatcomplexity__id__isnull=False,
                then=Concat(Cast("habitatcomplexity__transect__len_surveyed", CharField()), Value("m"))
            ),
            When(
                beltfish__id__isnull=False,
                then=Concat(
                    Cast("beltfish__transect__len_surveyed", CharField()),
                    Value("m x "),
                    Cast("beltfish__transect__width__val", CharField()),
                    Value("m")
                )
            ),
            When(
                bleachingquadratcollection__id__isnull=False,
                then=Concat(Cast("bleachingquadratcollection__quadrat__quadrat_size", CharField()), Value("m"))
            ),
        )

        qs = qs.annotate(
            protocol_name=protocol_condition,
            site_name=site_name_condition,
            management_name=management_name_condition,
            sample_unit_number=sample_unit_number_condition,
            depth=depth_condition,
            sample_date=sample_date_condition,
            size_display=size_condition,
        )

        return qs

    def filter_queryset(self, queryset):
        qs = super(SampleUnitMethodView, self).filter_queryset(queryset)
        if "ordering" in self.request.query_params:
            order_by = []
            for s in self.request.query_params["ordering"].split(","):
                s = s.strip()
                field = s[1:] if s.startswith("-") else s
                if field in self.ordering_fields:
                    order_by.append(s)
            if order_by:
                qs = qs.order_by(*order_by)
        return qs

    def limit_to_project(self, request, *args, **kwargs):
        prj_pk = check_uuid(kwargs["project_pk"])
        self.queryset = self.get_queryset().filter(
            Q(benthiclit__transect__sample_event__site__project=prj_pk)
            | Q(benthicpit__transect__sample_event__site__project=prj_pk)
            | Q(habitatcomplexity__transect__sample_event__site__project=prj_pk)
            | Q(beltfish__transect__sample_event__site__project=prj_pk)
            | Q(bleachingquadratcollection__quadrat__sample_event__site__project=prj_pk)
        )
        return self.queryset

    def get_serializer_context(self):
        context = super(SampleUnitMethodView, self).get_serializer_context()
        transect_method_ids = [r.id for r in self.get_queryset()]
        observers = mermaid.Observer.objects.filter(
            transectmethod_id__in=transect_method_ids
        )
        observer_lookup = defaultdict(list)
        for obs in observers:
            observer_lookup[str(obs.transectmethod_id)].append(obs.profile_name)

        context["observers"] = observer_lookup
        return context

    def retrieve(self, request, pk=None, **kwargs):

        # Disable the detail fetch - the subclass endpoints
        # should be used for SampleUnitMethod details
        raise exceptions.NotFound(code=404)
