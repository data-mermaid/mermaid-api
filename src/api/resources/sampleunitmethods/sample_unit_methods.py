import re
from collections import defaultdict

import django_filters
from django.contrib.postgres.aggregates import StringAgg
from django.db.models import Case, CharField, Q, Value, When
from django.db.models.functions import Cast, Concat
from rest_framework import exceptions, serializers

from ...exceptions import check_uuid
from ...models import mermaid
from ...models.mermaid import SampleEvent, TransectMethod
from ..base import BaseAPIFilterSet, BaseAPISerializer, BaseProjectApiViewSet


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

        try:
            re.compile(value)
        except re.error:
            raise exceptions.ValidationError("Invalid search")

        qry = Q()
        for field in self.SEARCH_FIELDS:
            qry |= Q(**{"{}__iregex".format(field): value})
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
        protocol = o.protocol
        if protocol == mermaid.FISHBELT_PROTOCOL:
            sample_unit = o.sample_unit

            return dict(
                width=sample_unit.width.id,
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
    queryset = TransectMethod.objects.select_related(
        "benthiclit",
        "benthicpit",
        "habitatcomplexity",
        "beltfish",
        "bleachingquadratcollection",
        "benthicphotoquadrattransect",
        "benthicpit__transect",
        "benthiclit__transect",
        "beltfish__transect",
        "habitatcomplexity__transect",
        "bleachingquadratcollection__quadrat",
        "benthicphotoquadrattransect__quadrat_transect",
    ).all()

    filterset_class = SampleUnitMethodFilterSet
    serializer_class = SampleUnitMethodSerializer
    http_method_names = ["get", "head"]

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
            When(
                benthicphotoquadrattransect__id__isnull=False,
                then=Value(mermaid.BENTHICPQT_PROTOCOL),
            ),
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
            When(
                benthicphotoquadrattransect__quadrat_transect__sample_event__site__name__isnull=False,
                then="benthicphotoquadrattransect__quadrat_transect__sample_event__site__name",
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
            When(
                benthicphotoquadrattransect__quadrat_transect__sample_event__management__name__isnull=False,
                then="benthicphotoquadrattransect__quadrat_transect__sample_event__management__name",
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
            When(
                benthicphotoquadrattransect__quadrat_transect__number__isnull=False,
                then="benthicphotoquadrattransect__quadrat_transect__number",
            ),
        )

        depth_condition = Case(
            When(
                benthiclit__transect__depth__isnull=False,
                then="benthiclit__transect__depth",
            ),
            When(
                benthicpit__transect__depth__isnull=False,
                then="benthicpit__transect__depth",
            ),
            When(
                habitatcomplexity__transect__depth__isnull=False,
                then="habitatcomplexity__transect__depth",
            ),
            When(
                bleachingquadratcollection__quadrat__depth__isnull=False,
                then="bleachingquadratcollection__quadrat__depth",
            ),
            When(
                beltfish__transect__depth__isnull=False,
                then="beltfish__transect__depth",
            ),
            When(
                benthicphotoquadrattransect__quadrat_transect__depth__isnull=False,
                then="benthicphotoquadrattransect__quadrat_transect__depth",
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
            When(
                benthicphotoquadrattransect__quadrat_transect__sample_event__sample_date__isnull=False,
                then="benthicphotoquadrattransect__quadrat_transect__sample_event__sample_date",
            ),
        )

        size_condition = Case(
            When(
                benthiclit__id__isnull=False,
                then=Concat(Cast("benthiclit__transect__len_surveyed", CharField()), Value("m")),
            ),
            When(
                benthicpit__id__isnull=False,
                then=Concat(Cast("benthicpit__transect__len_surveyed", CharField()), Value("m")),
            ),
            When(
                habitatcomplexity__id__isnull=False,
                then=Concat(
                    Cast("habitatcomplexity__transect__len_surveyed", CharField()),
                    Value("m"),
                ),
            ),
            When(
                benthicphotoquadrattransect__id__isnull=False,
                then=Concat(
                    Cast(
                        "benthicphotoquadrattransect__quadrat_transect__len_surveyed", CharField()
                    ),
                    Value("m"),
                ),
            ),
            When(
                beltfish__id__isnull=False,
                then=Concat(
                    Cast("beltfish__transect__len_surveyed", CharField()),
                    Value("m x "),
                    Cast("beltfish__transect__width__name", CharField()),
                ),
            ),
            When(
                bleachingquadratcollection__id__isnull=False,
                then=Concat(
                    Cast("bleachingquadratcollection__quadrat__quadrat_size", CharField()),
                    Value("m"),
                ),
            ),
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

        qs = qs.annotate(
            protocol_name=protocol_condition,
            site_name=site_name_condition,
            management_name=management_name_condition,
            sample_unit_number=sample_unit_number_condition,
            sample_unit_method_depth=depth_condition,
            sample_date=sample_date_condition,
            size_display=size_condition,
            observers_display=observers,
        )

        return qs

    def limit_to_project(self, request, *args, **kwargs):
        prj_pk = check_uuid(kwargs["project_pk"])
        self.queryset = self.get_queryset().filter(
            Q(benthiclit__transect__sample_event__site__project=prj_pk)
            | Q(benthicpit__transect__sample_event__site__project=prj_pk)
            | Q(habitatcomplexity__transect__sample_event__site__project=prj_pk)
            | Q(beltfish__transect__sample_event__site__project=prj_pk)
            | Q(bleachingquadratcollection__quadrat__sample_event__site__project=prj_pk)
            | Q(benthicphotoquadrattransect__quadrat_transect__sample_event__site__project=prj_pk)
        )
        return self.queryset

    def get_serializer_context(self):
        context = super(SampleUnitMethodView, self).get_serializer_context()
        transect_method_ids = []
        sample_event_ids = []
        for r in self.get_queryset():
            transect_method_ids.append(r.id)
            sample_event_ids.append(r.sample_unit.sample_event_id)

        context["sample_events"] = {
            str(se.id): se
            for se in SampleEvent.objects.select_related("site", "management").filter(
                id__in=set(sample_event_ids)
            )
        }

        observers = mermaid.Observer.objects.select_related("profile").filter(
            transectmethod_id__in=transect_method_ids
        )
        observer_lookup = defaultdict(list)
        for obs in observers:
            observer_lookup[str(obs.transectmethod_id)].append(obs.profile_name)
        for transect_method_id, observers in observer_lookup.items():
            observer_lookup[transect_method_id] = sorted(observers)

        context["observers"] = observer_lookup
        return context

    def retrieve(self, request, pk=None, **kwargs):
        # Disable the detail fetch - the method-specific endpoints
        # should be used for SampleUnitMethod details
        raise exceptions.NotFound(code=404)
