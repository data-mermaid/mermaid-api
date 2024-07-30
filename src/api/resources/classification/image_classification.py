from rest_framework import serializers

from ...models import ClassificationStatus
from ..base import BaseAPISerializer


class ClassificationStatusSerializer(BaseAPISerializer):

    class Meta:
        model = ClassificationStatus
        fields = ["status", "message", "data"]
