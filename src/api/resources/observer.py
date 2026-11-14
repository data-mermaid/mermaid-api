from rest_framework import serializers

from ..exceptions import check_uuid
from ..models import Observer, TransectMethod
from .base import (
    BaseAPIFilterSet,
    BaseAPISerializer,
    BaseProjectApiViewSet,
    ExtendedSerializer,
)


class ObserverExtendedSerializer(ExtendedSerializer):
    profile_name = serializers.ReadOnlyField()

    class Meta:
        model = Observer
        exclude = []


class ObserverSerializer(BaseAPISerializer):
    profile_name = serializers.ReadOnlyField()

    class Meta:
        model = Observer
        exclude = []


class ObserverFilterSet(BaseAPIFilterSet):
    class Meta:
        model = Observer
        fields = [
            "transectmethod",
            "profile",
            "rank",
        ]


class ObserverViewSet(BaseProjectApiViewSet):
    serializer_class = ObserverSerializer
    # profile_name falls back to Profile.num_account_connections for nameless profiles
    queryset = Observer.objects.select_related("profile").prefetch_related("profile__authusers")
    filterset_class = ObserverFilterSet
    search_fields = ["profile__first_name", "profile__last_name"]
    ordering = ["transectmethod", "rank"]

    def perform_update(self, serializer):
        serializer.save()

    def limit_to_project(self, request, *args, **kwargs):
        prj_pk = check_uuid(kwargs["project_pk"])
        # One subquery per protocol, so new TransectMethod subclasses are included
        # automatically; much faster than OR-ing joins across every protocol table.
        method_ids = [
            method_cls.objects.filter(**{method_cls.project_lookup: prj_pk}).values("pk")
            for method_cls in TransectMethod.__subclasses__()
        ]
        self.queryset = self.get_queryset().filter(
            transectmethod_id__in=method_ids[0].union(*method_ids[1:], all=True)
        )
        return self.queryset
