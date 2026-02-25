from django.utils.dateparse import parse_date
from rest_framework.exceptions import ParseError

from ....exceptions import check_uuid
from ..statuses import ERROR, OK, WARN
from ..utils import PROTOCOL_MODEL_MAP, PROTOCOL_SAMPLE_EVENT_PATH, valid_id
from .base import BaseValidator, validator_result


class SimilarDateSampleUnitsValidator(BaseValidator):
    SIMILAR_DATE_SAMPLE_UNIT = "similar_date_sample_unit"
    UNKNOWN_PROTOCOL = "unknown_protocol"

    def __init__(
        self,
        protocol_path,
        site_path,
        management_path,
        sample_date_path,
        days_threshold=30,
        **kwargs,
    ):
        self.protocol_path = protocol_path
        self.site_path = site_path
        self.management_path = management_path
        self.sample_date_path = sample_date_path
        self.days_threshold = days_threshold
        super().__init__(**kwargs)

    @validator_result
    def __call__(self, collect_record, **kwargs):
        protocol = self.get_value(collect_record, self.protocol_path)
        site_id = valid_id(self.get_value(collect_record, self.site_path))
        management_id = valid_id(self.get_value(collect_record, self.management_path))
        sample_date_str = self.get_value(collect_record, self.sample_date_path)

        # Skip validation if required values are missing
        if not protocol or not site_id or not management_id or not sample_date_str:
            return OK

        try:
            check_uuid(site_id)
            check_uuid(management_id)
            sample_date = parse_date(sample_date_str)
            if sample_date is None:
                return OK  # Let other validators handle invalid dates
        except (ValueError, TypeError, ParseError):
            return OK  # Let other validators handle invalid data

        model = PROTOCOL_MODEL_MAP.get(protocol)
        sample_event_path = PROTOCOL_SAMPLE_EVENT_PATH.get(protocol)

        if not model or not sample_event_path:
            return ERROR, self.UNKNOWN_PROTOCOL, {"protocol": protocol}

        queryset = model.objects.filter(
            **{
                f"{sample_event_path}__site_id": site_id,
                f"{sample_event_path}__management_id": management_id,
            }
        ).select_related(sample_event_path)

        parts = sample_event_path.split("__")
        similar_dates = []
        for su in queryset:
            su_sample_event = su
            for part in parts:
                su_sample_event = getattr(su_sample_event, part)

            su_date = su_sample_event.sample_date
            days_difference = abs((su_date - sample_date).days)

            # Only warn if date difference is between 1 and threshold days (inclusive)
            # Same day (0 days) should not trigger a warning
            if 1 <= days_difference <= self.days_threshold:
                similar_dates.append({"date": str(su_date), "days_difference": days_difference})

        if similar_dates:
            # Find the minimum days difference (closest match)
            min_days_difference = min(sd["days_difference"] for sd in similar_dates)
            return (
                WARN,
                self.SIMILAR_DATE_SAMPLE_UNIT,
                {
                    "protocol": protocol,
                    "days_difference": min_days_difference,
                    "similar_dates": similar_dates,
                },
            )

        return OK
