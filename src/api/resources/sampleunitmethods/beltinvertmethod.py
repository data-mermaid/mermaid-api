from decimal import Decimal

from rest_framework import serializers

from ...models import BeltInvert, ObsBeltInvert
from ..base import BaseAPISerializer

__all__ = ["BeltInvertSerializer", "ObsBeltInvertSerializer"]


class BeltInvertSerializer(BaseAPISerializer):
    class Meta:
        model = BeltInvert
        exclude = []


class ObsBeltInvertSerializer(BaseAPISerializer):
    size = serializers.DecimalField(
        max_digits=5,
        decimal_places=1,
        coerce_to_string=False,
        allow_null=True,
        required=False,
        min_value=Decimal("0.1"),
    )

    class Meta:
        model = ObsBeltInvert
        exclude = []
        extra_kwargs = {
            "invert_attribute": {
                "error_messages": {
                    "does_not_exist": 'Invert attribute with id "{pk_value}", does not exist.'
                }
            }
        }
