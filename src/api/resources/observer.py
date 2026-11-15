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
    profile_name = serializers.SerializerMethodField()

    def get_profile_name(self, o):
        # profile_name can COUNT the profile's authusers (nameless profiles); once per profile
        names = self.context.setdefault("_profile_names", {})
        if o.profile_id not in names:
            names[o.profile_id] = o.profile_name
        return names[o.profile_id]

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
    queryset = Observer.objects.select_related("profile")
    filterset_class = ObserverFilterSet
    search_fields = ["profile__first_name", "profile__last_name"]
    ordering = ["transectmethod", "rank"]

    def perform_update(self, serializer):
        serializer.save()

    def limit_to_project(self, request, *args, **kwargs):
        prj_pk = check_uuid(kwargs["project_pk"])
        self.queryset = self.get_queryset().filter(
            transectmethod_id__in=TransectMethod.project_method_ids(prj_pk)
        )
        return self.queryset
