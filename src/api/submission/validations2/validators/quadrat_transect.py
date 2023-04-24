from django.utils.dateparse import parse_date
from rest_framework.exceptions import ParseError

from ....exceptions import check_uuid
from ....models import QuadratTransect
from ....utils import get_related_transect_methods
from .base import ERROR, OK, ERROR, BaseValidator, validator_result


class UniqueQuadratTransectValidator(BaseValidator):
    INVALID_DATA = "invalid_quadrat_transect"
    DUPLICATE_QUADRAT_TRANSECT = "duplicate_quadrat_transect"

    def __init__(
        self,
        protocol_path,
        label_path,
        number_path,
        site_path,
        management_path,
        sample_date_path,
        depth_path,
        observers_path,
        **kwargs,
    ):
        self.protocol_path = protocol_path
        self.label_path = label_path
        self.number_path = number_path
        self.site_path = site_path
        self.management_path = management_path
        self.sample_date_path = sample_date_path
        self.depth_path = depth_path
        self.observers_path = observers_path

        super().__init__(**kwargs)

    def _get_query_args(self, collect_record):
        label = self.get_value(collect_record, self.label_path) or ""
        number = self.get_value(collect_record, self.number_path) or None
        site = self.get_value(collect_record, self.site_path) or None
        management = self.get_value(collect_record, self.management_path) or None
        sample_date = self.get_value(collect_record, self.sample_date_path) or None
        depth = self.get_value(collect_record, self.depth_path) or None
        observers = self.get_value(collect_record, self.observers_path) or []
        profiles = [o.get("profile") for o in observers]

        try:
            number = int(number)
            check_uuid(site)
            check_uuid(management)
            float(depth)
            if parse_date(f"{sample_date}") is None:
                raise ValueError()
            for profile in profiles:
                _ = check_uuid(profile)
        except (ValueError, TypeError, ParseError) as e:
            raise ParseError() from e

        return {
            "sample_event__site": site,
            "sample_event__management": management,
            "sample_event__sample_date": sample_date,
            "number": number,
            "label": label,
            "depth": depth,
        }, profiles

    def _check_for_duplicate_transect_methods(self, transect_methods, protocol):
        for transect_method in transect_methods:
            if transect_method.protocol == protocol:
                return (
                    ERROR,
                    self.DUPLICATE_QUADRAT_TRANSECT,
                    {"duplicate_transect_method": str(transect_method.pk)},
                )
        return OK

    @validator_result
    def __call__(self, collect_record, **kwargs):
        protocol = self.get_value(collect_record, self.protocol_path)

        try:
            qry, profiles = self._get_query_args(collect_record)
        except ParseError:
            return ERROR, self.INVALID_DATA

        queryset = QuadratTransect.objects.select_related().filter(**qry)

        for profile in profiles:
            queryset = queryset.filter(benthic_photo_quadrat_transect_method__observers__profile_id=profile)

        for result in queryset:
            transect_methods = get_related_transect_methods(result)
            duplicate_check = self._check_for_duplicate_transect_methods(
                transect_methods, protocol
            )
            if duplicate_check != OK:
                return duplicate_check
        return OK
