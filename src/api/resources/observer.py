from django.db.models import Q
from rest_framework import serializers

from ..exceptions import check_uuid
from ..models import Observer
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
    queryset = Observer.objects.all()
    filterset_class = ObserverFilterSet
    search_fields = ["profile__first_name", "profile__last_name"]

    def perform_update(self, serializer):
        serializer.save()

    def limit_to_project(self, request, *args, **kwargs):
        prj_pk = check_uuid(kwargs["project_pk"])
        self.queryset = self.get_queryset().filter(
            Q(transectmethod__benthiclit__transect__sample_event__site__project=prj_pk)
            | Q(transectmethod__benthicpit__transect__sample_event__site__project=prj_pk)
            | Q(transectmethod__habitatcomplexity__transect__sample_event__site__project=prj_pk)
            | Q(transectmethod__beltfish__transect__sample_event__site__project=prj_pk)
            | Q(
                transectmethod__bleachingquadratcollection__quadrat__sample_event__site__project=prj_pk
            )
        )
        return self.queryset
