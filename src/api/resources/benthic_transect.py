import django_filters
from base import BaseAPIFilterSet, BaseProjectApiViewSet, BaseAPISerializer
from ..models import BenthicTransect


class BenthicTransectSerializer(BaseAPISerializer):

    class Meta:
        model = BenthicTransect
        exclude = []
        extra_kwargs = {
            "len_surveyed": {
                "error_messages": {"null": "Transect length surveyed is required"}
            },
            "number": {
                "error_messages": {"null": "Transect Number is required"}
            }
        }


class BenthicTransectFilterSet(BaseAPIFilterSet):
    len_surveyed = django_filters.NumericRangeFilter(name='len_surveyed')

    class Meta:
        model = BenthicTransect
        fields = ['benthiclit_method', 'benthicpit_method', 'habitatcomplexity_method', 'sample_event', 'len_surveyed', ]


class BenthicTransectViewSet(BaseProjectApiViewSet):
    serializer_class = BenthicTransectSerializer
    queryset = BenthicTransect.objects.all()
    filter_class = BenthicTransectFilterSet
