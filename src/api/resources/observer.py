from rest_framework import serializers

from base import (
    BaseAPIFilterSet,
    BaseProjectApiViewSet,
    BaseAPISerializer,
    ExtendedSerializer,
    ModelNameReadOnlyField,
)
from ..models import Observer


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
        fields = ['transectmethod', 'profile', 'rank', ]


class ObserverViewSet(BaseProjectApiViewSet):
    serializer_class = ObserverSerializer
    queryset = Observer.objects.all()
    filter_class = ObserverFilterSet
    search_fields = ['profile__first_name', 'profile__last_name']
