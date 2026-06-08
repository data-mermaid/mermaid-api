from decimal import Decimal

import django_filters
from rest_framework.serializers import DecimalField

from ..models import Management
from .base import (
    BaseAPIFilterSet,
    BaseAPISerializer,
    BaseProjectApiViewSet,
    NullableUUIDFilter,
)
from .management import get_rules
from .mixins import (
    CopyRecordsMixin,
    CreateOrUpdateSerializerMixin,
    NotifyDeletedSiteMRMixin,
)


class PManagementSerializer(CreateOrUpdateSerializerMixin, BaseAPISerializer):
    size = DecimalField(
        max_digits=12,
        decimal_places=3,
        coerce_to_string=False,
        required=False,
        allow_null=True,
        min_value=Decimal("0.001"),
    )

    class Meta:
        model = Management
        exclude = []


def to_governance(field, row, serializer_instance):
    parties = ""
    project_pk = row.get("project_id")
    management_id = row.get("id")
    lookup = serializer_instance.serializer_cache.get("management_parties-{}".format(project_pk))
    if lookup:
        parties = lookup.get(str(management_id))
    else:
        management = Management.objects.get_or_none(id=management_id)
        if management is not None:
            mps = management.parties.all().iterator()
            parties = ",".join([mp.name for mp in mps])
    return parties


def to_management_rules(field, row, serializer_instance):
    project_pk = row.get("project_id")
    management_id = row.get("id")
    lookup = serializer_instance.serializer_cache.get("management_rules-{}".format(project_pk))
    if lookup:
        return lookup.get(str(management_id))

    return get_rules(Management.objects.get_or_none(id=management_id))


class PManagementFilterSet(BaseAPIFilterSet):
    predecessor = NullableUUIDFilter(field_name="predecessor")
    compliance = NullableUUIDFilter(field_name="compliance")
    est_year = django_filters.RangeFilter(field_name="est_year")

    class Meta:
        model = Management
        fields = [
            "predecessor",
            "parties",
            "compliance",
            "est_year",
            "no_take",
            "periodic_closure",
            "open_access",
            "size_limits",
            "gear_restriction",
            "species_restriction",
            "access_restriction",
        ]


class PManagementViewSet(NotifyDeletedSiteMRMixin, CopyRecordsMixin, BaseProjectApiViewSet):
    model_display_name = "Management Regime"
    serializer_class = PManagementSerializer
    queryset = Management.objects.all()
    project_lookup = "project"
    filterset_class = PManagementFilterSet
    search_fields = [
        "name",
        "name_secondary",
    ]
