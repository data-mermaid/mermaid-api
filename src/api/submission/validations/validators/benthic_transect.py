import math

from django.utils.dateparse import parse_date
from rest_framework.exceptions import ParseError

from ....exceptions import check_uuid
from ....models import BenthicTransect
from ....utils import cast_float, get_related_transect_methods
from ..statuses import ERROR, OK
from .base import BaseValidator, validator_result


class UniqueBenthicTransectValidator(BaseValidator):
    INVALID_DATA = "invalid_benthic_transect"
    DUPLICATE_BENTHIC_TRANSECT = "duplicate_benthic_transect"

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
                    self.DUPLICATE_BENTHIC_TRANSECT,
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

        queryset = BenthicTransect.objects.select_related().filter(**qry)

        for profile in profiles:
            key = f"{protocol}_method__observers__profile_id"
            queryset = queryset.filter(**{key: profile})

        for result in queryset:
            transect_methods = get_related_transect_methods(result)
            duplicate_check = self._check_for_duplicate_transect_methods(transect_methods, protocol)
            if duplicate_check != OK:
                return duplicate_check
        return OK


class BenthicIntervalObservationCountValidator(BaseValidator):
    """
    Length surveyed
    ---------------  == Observation count
     Interval size
    """

    INCORRECT_OBSERVATION_COUNT = "incorrect_observation_count"
    NON_POSITIVE = "{}_not_positive"

    def __init__(self, len_surveyed_path, interval_size_path, observations_path, **kwargs):
        self.len_surveyed_path = len_surveyed_path
        self.interval_size_path = interval_size_path
        self.observations_path = observations_path
        super().__init__(**kwargs)

    @validator_result
    def __call__(self, collect_record, **kwargs):
        tolerance = 1
        observations = self.get_value(collect_record, self.observations_path) or []
        observations_count = len(observations)
        len_surveyed = cast_float(self.get_value(collect_record, self.len_surveyed_path))
        interval_size = cast_float(self.get_value(collect_record, self.interval_size_path))

        # Treat None as invalid (not positive)
        if len_surveyed is None or len_surveyed <= 0:
            return ERROR, self.NON_POSITIVE.format("len_surveyed")
        if interval_size is None or interval_size <= 0:
            return ERROR, self.NON_POSITIVE.format("interval_size")

        calc_obs_count = int(math.ceil(len_surveyed / interval_size))
        if (
            observations_count > calc_obs_count + tolerance
            or observations_count < calc_obs_count - tolerance
        ):
            return (
                ERROR,
                self.INCORRECT_OBSERVATION_COUNT,
                {"expected_count": calc_obs_count},
            )

        return OK


class IntervalSequenceValidator(BaseValidator):
    MISSING_INTERVALS = "missing_intervals"
    TOLERANCE = 0.0001

    def __init__(
        self,
        len_surveyed_path,
        interval_size_path,
        interval_start_path,
        observations_path,
        observation_interval_path,
        **kwargs,
    ):
        self.len_surveyed_path = len_surveyed_path
        self.interval_size_path = interval_size_path
        self.interval_start_path = interval_start_path
        self.observations_path = observations_path
        self.observation_interval_path = observation_interval_path
        super().__init__(**kwargs)

    @validator_result
    def __call__(self, collect_record, **kwargs):
        len_surveyed = cast_float(self.get_value(collect_record, self.len_surveyed_path))
        interval_size = cast_float(self.get_value(collect_record, self.interval_size_path))
        interval_start = cast_float(self.get_value(collect_record, self.interval_start_path))
        observations = self.get_value(collect_record, self.observations_path) or []

        # Skip validation if required values are missing or invalid
        if len_surveyed is None or len_surveyed <= 0 or not math.isfinite(len_surveyed):
            return OK
        if interval_size is None or interval_size <= 0 or not math.isfinite(interval_size):
            return OK
        if interval_start is None or interval_start < 0 or not math.isfinite(interval_start):
            return OK

        actual_intervals = []
        for obs in observations:
            interval = cast_float(self.get_value(obs, self.observation_interval_path))
            if interval is not None:
                actual_intervals.append(interval)

        expected_intervals = []
        n = 0
        # Calculate each interval independently to avoid floating-point accumulation errors
        while True:
            interval = interval_start + n * interval_size
            if interval > len_surveyed + self.TOLERANCE:
                break
            # Round to avoid floating-point representation issues in error messages
            expected_intervals.append(round(interval, 10))
            n += 1

        missing_intervals = []
        for expected in expected_intervals:
            # Check if any actual interval is close enough to this expected interval
            found = any(abs(actual - expected) <= self.TOLERANCE for actual in actual_intervals)
            if not found:
                missing_intervals.append(expected)

        if missing_intervals:
            return (
                ERROR,
                self.MISSING_INTERVALS,
                {"missing_intervals": missing_intervals},
            )

        return OK


class IntervalAlignmentValidator(BaseValidator):
    INVALID_INTERVALS = "invalid_intervals"
    TOLERANCE = 0.0001

    def __init__(
        self,
        interval_size_path,
        interval_start_path,
        observations_path,
        observation_interval_path,
        **kwargs,
    ):
        self.interval_size_path = interval_size_path
        self.interval_start_path = interval_start_path
        self.observations_path = observations_path
        self.observation_interval_path = observation_interval_path
        super().__init__(**kwargs)

    @validator_result
    def __call__(self, collect_record, **kwargs):
        interval_size = cast_float(self.get_value(collect_record, self.interval_size_path))
        interval_start = cast_float(self.get_value(collect_record, self.interval_start_path))
        observations = self.get_value(collect_record, self.observations_path) or []

        # Skip validation if required values are missing or invalid
        if interval_size is None or interval_size <= 0:
            return OK
        if interval_start is None or interval_start < 0:
            return OK

        # Check that each interval is aligned to the grid: interval_start + n × interval_size
        invalid_intervals = []
        for obs in observations:
            interval = cast_float(self.get_value(obs, self.observation_interval_path))
            if interval is None:
                continue

            offset = interval - interval_start
            # Check if offset is a multiple of interval_size (within floating point tolerance)
            if offset < 0:
                # Interval is before start
                invalid_intervals.append(interval)
            else:
                # Check if offset/interval_size is close to an integer
                quotient = offset / interval_size
                remainder = abs(quotient - round(quotient))
                is_aligned = remainder <= self.TOLERANCE
                if not is_aligned:
                    invalid_intervals.append(interval)

        if invalid_intervals:
            return (
                ERROR,
                self.INVALID_INTERVALS,
                {
                    "invalid_intervals": invalid_intervals,
                    "interval_start": interval_start,
                    "interval_size": interval_size,
                },
            )

        return OK
