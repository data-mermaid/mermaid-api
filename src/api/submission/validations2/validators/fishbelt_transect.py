from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import ParseError

from ....exceptions import check_uuid
from ....models import FishBeltTransect
from ....utils import get_related_transect_methods
from .base import ERROR, OK, ERROR, BaseValidator, validator_result


class UniqueFishbeltTransectValidator(BaseValidator):
    INVALID_INPUTS = "invalid_transect_inputs"
    DUPLICATE_TRANSECT = "duplicate_transect"

    def __init__(
        self,
        protocol,
        label_path,
        number_path,
        width_path,
        site_path,
        management_path,
        sample_date_path,
        depth_path,
        observers_path,
        **kwargs,
    ):
        self.protocol = protocol
        self.label_path = label_path
        self.number_path = number_path
        self.width_path = width_path
        self.site_path = site_path
        self.management_path = management_path
        self.sample_date_path = sample_date_path
        self.depth_path = depth_path
        self.observers_path = observers_path

        super().__init__(**kwargs)

    def _get_query_args(self, collect_record):
        label = self.get_value(collect_record, self.label_path) or ""
        number = self.get_value(collect_record, self.number_path) or None
        width = self.get_value(collect_record, self.width_path) or None
        site = self.get_value(collect_record, self.site_path) or None
        management = self.get_value(collect_record, self.management_path) or None
        sample_date = self.get_value(collect_record, self.sample_date_path) or None
        depth = self.get_value(collect_record, self.depth_path) or None
        observers = self.get_value(collect_record, self.observers_path) or []
        profiles = [o.get("profile") for o in observers]

        try:
            number = int(number)
            check_uuid(width)
            check_uuid(site)
            check_uuid(management)
            if parse_datetime(f"{sample_date} 00:00:00") is None:
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
            "width_id": width,
        }, profiles

    def _check_for_duplicate_transect_methods(self, transect_methods, protocol):
        for transect_method in transect_methods:
            if transect_method.protocol == protocol:
                return (
                    ERROR,
                    self.DUPLICATE_TRANSECT,
                    {"duplicate_transect_method": str(transect_method.pk)},
                )
        return OK

    @validator_result
    def __call__(self, collect_record, **kwargs):
        try:
            qry, profiles = self._get_query_args(collect_record)
        except ParseError:
            return ERROR, self.INVALID_INPUTS

        queryset = FishBeltTransect.objects.select_related().filter(**qry)

        for profile in profiles:
            queryset = queryset.filter(beltfish_method__observers__profile_id=profile)

        for result in queryset:
            transect_methods = get_related_transect_methods(result)
            duplicate_check = self._check_for_duplicate_transect_methods(
                transect_methods, self.protocol
            )
            if duplicate_check != OK:
                return duplicate_check
        return OK
