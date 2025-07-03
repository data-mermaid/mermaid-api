from django.utils.dateparse import parse_date
from rest_framework.exceptions import ParseError

from ....exceptions import check_uuid
from ....models import QuadratCollection
from ....utils import get_related_transect_methods
from .base import ERROR, OK, BaseValidator, validator_result


class UniqueQuadratCollectionValidator(BaseValidator):
    INVALID_DATA = "invalid_quadrat_collection"
    DUPLICATE_QUADRAT_COLLECTION = "duplicate_quadrat_collection"

    def __init__(
        self,
        protocol_path,
        site_path,
        management_path,
        sample_date_path,
        label_path,
        depth_path,
        observers_path,
        **kwargs,
    ):
        self.protocol_path = protocol_path
        self.site_path = site_path
        self.management_path = management_path
        self.sample_date_path = sample_date_path
        self.label_path = label_path
        self.depth_path = depth_path
        self.observers_path = observers_path
        super().__init__(**kwargs)

    @validator_result
    def __call__(self, collect_record, **kwargs):
        protocol = self.get_value(collect_record, self.protocol_path)
        site_id = self.get_value(collect_record, self.site_path)
        management_id = self.get_value(collect_record, self.management_path)
        sample_date = self.get_value(collect_record, self.sample_date_path)
        label = self.get_value(collect_record, self.label_path)
        depth = self.get_value(collect_record, self.depth_path)
        observers = self.get_value(collect_record, self.observers_path) or []

        profiles = [o.get("profile") for o in observers]

        try:
            check_uuid(site_id)
            check_uuid(management_id)
            float(depth)
            if parse_date(f"{sample_date}") is None:
                raise ValueError()
            for profile in profiles:
                _ = check_uuid(profile)
        except (ParseError, ValueError, TypeError):
            return ERROR, self.INVALID_DATA

        qry = {
            "sample_event__site": site_id,
            "sample_event__management": management_id,
            "sample_event__sample_date": sample_date,
            "depth": depth,
        }
        if label:
            qry["label"] = label

        queryset = QuadratCollection.objects.filter(**qry)
        for profile in profiles:
            queryset = queryset.filter(
                bleachingquadratcollection_method__observers__profile_id=profile
            )

        for result in queryset:
            transect_methods = get_related_transect_methods(result)
            for transect_method in transect_methods:
                if transect_method.protocol == protocol:
                    return ERROR, self.DUPLICATE_QUADRAT_COLLECTION

        return OK
