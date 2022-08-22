from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from api.models import (
    BenthicLIT,
    ObsBenthicLIT,
    BeltFish,
    ObsBeltFish,
    BenthicPIT,
    ObsBenthicPIT,
    HabitatComplexity,
    ObsHabitatComplexity,
    BleachingQuadratCollection,
    ObsColoniesBleached,
    ObsQuadratBenthicPercent,
    BenthicPhotoQuadratTransect,
    ObsBenthicPhotoQuadrat,
)
from api.resources.base import BaseAPISerializer


class BeltFishSerializer(BaseAPISerializer):
    class Meta:
        model = BeltFish
        exclude = []


class BenthicLITSerializer(BaseAPISerializer):
    class Meta:
        model = BenthicLIT
        exclude = []


class BenthicPhotoQuadratTransectSerializer(BaseAPISerializer):
    class Meta:
        model = BenthicPhotoQuadratTransect
        exclude = []


class BenthicPITSerializer(BaseAPISerializer):
    interval_size = serializers.DecimalField(
        max_digits=4,
        decimal_places=2,
        coerce_to_string=False,
        error_messages={"null": "Interval size is required"},
    )

    interval_start = serializers.DecimalField(
        max_digits=4,
        decimal_places=2,
        coerce_to_string=False,
        error_messages={"null": "Interval start is required"},
    )

    class Meta:
        model = BenthicPIT
        exclude = []


class BleachingQuadratCollectionSerializer(BaseAPISerializer):
    class Meta:
        model = BleachingQuadratCollection
        exclude = []
        extra_kwargs = {}


class HabitatComplexitySerializer(BaseAPISerializer):
    interval_size = serializers.DecimalField(
        max_digits=4,
        decimal_places=2,
        coerce_to_string=False,
        error_messages={"null": "Interval size is required"},
    )

    class Meta:
        model = HabitatComplexity
        exclude = []


class ObsBeltFishSerializer(BaseAPISerializer):
    size = serializers.DecimalField(
        max_digits=5, decimal_places=1, coerce_to_string=False
    )

    class Meta:
        model = ObsBeltFish
        exclude = []
        extra_kwargs = {
            "fish_attribute": {
                "error_messages": {
                    "does_not_exist": 'Fish attribute with id "{pk_value}", does not exist.'
                }
            }
        }


class ObsBenthicLITSerializer(BaseAPISerializer):
    class Meta:
        model = ObsBenthicLIT
        exclude = []
        extra_kwargs = {
            "attribute": {
                "error_messages": {
                    "does_not_exist": 'Benthic attribute with id "{pk_value}", does not exist.'
                }
            }
        }


class ObsBenthicPhotoQuadratSerializer(BaseAPISerializer):
    class Meta:
        model = ObsBenthicPhotoQuadrat
        exclude = []
        extra_kwargs = {
            "attribute": {
                "error_messages": {
                    "does_not_exist": 'Benthic attribute with id "{pk_value}", does not exist.'
                }
            }
        }


class ObsBenthicPITSerializer(BaseAPISerializer):
    class Meta:
        model = ObsBenthicPIT
        exclude = []
        extra_kwargs = {
            "attribute": {
                "error_messages": {
                    "does_not_exist": 'Benthic attribute with id "{pk_value}", does not exist.'
                }
            }
        }


class ObsColoniesBleachedSerializer(BaseAPISerializer):
    class Meta:
        model = ObsColoniesBleached
        exclude = []
        extra_kwargs = {
            "attribute": {
                "error_messages": {
                    "does_not_exist": 'Benthic attribute with id "{pk_value}", does not exist.'
                }
            }
        }


class ObsQuadratBenthicPercentSerializer(BaseAPISerializer):
    class Meta:
        model = ObsQuadratBenthicPercent
        exclude = []
        extra_kwargs = {
            "quadrat_number": {"error_messages": {"null": "Quadrat number is required"}}
        }
        validators = [
            UniqueTogetherValidator(
                queryset=ObsQuadratBenthicPercent.objects.all(),
                fields=["bleachingquadratcollection", "quadrat_number"],
                message="Duplicate quadrat numbers",
            )
        ]


class ObsHabitatComplexitySerializer(BaseAPISerializer):
    class Meta:
        model = ObsHabitatComplexity
        exclude = []
