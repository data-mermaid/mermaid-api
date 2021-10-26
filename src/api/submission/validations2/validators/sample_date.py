from dateutil import tz
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from timezonefinder import TimezoneFinder

from api.models import Site
from .base import ERROR, OK, WARN, BaseValidator, validator_result


class SampleDateValidator(BaseValidator):
    INVALID_SAMPLE_DATE = "invalid_sample_date"
    FUTURE_SAMPLE_DATE = "future_sample_date"

    def __init__(self, sample_date_path, sample_time_path, site_path):
        self.sample_date_path = sample_date_path
        self.sample_time_path = sample_time_path
        self.site_path = site_path

    def is_sample_date(self, date_str):
        sample_date = parse_datetime(f"{date_str} 00:00:00")
        return sample_date is not None

    def is_future_sample_date(self, date_str, time_str, site_id):
        site = Site.objects.get_or_none(id=site_id)

        if site is None or site.location is None:
            return False

        x = site.location.x
        y = site.location.y

        tf = TimezoneFinder()
        tz_str = tf.timezone_at(lng=x, lat=y) or "UTC"
        tzinfo = tz.gettz(tz_str)
        sample_date = parse_datetime("{} {}".format(date_str, time_str))
        if sample_date is None:
            return False
        sample_date = sample_date.replace(tzinfo=tzinfo)
        todays_date = timezone.now().astimezone(tzinfo)
        delta = todays_date - sample_date

        return delta.days < 0

    @validator_result
    def __call__(self, collect_record, **kwargs):
        sample_date_str = self.get_value(collect_record, self.sample_date_path) or ""
        sample_time_str = self.get_value(collect_record, self.sample_time_path) or ""
        site_id = self.get_value(collect_record, self.site_path) or ""

        if sample_date_str.strip() == "":
            sample_date_str = None

        if sample_time_str.strip() == "":
            sample_time_str = None

        if self.is_sample_date(sample_date_str) is False:
            return ERROR, self.INVALID_SAMPLE_DATE

        if (
            self.is_future_sample_date(sample_date_str, sample_time_str, site_id)
            is True
        ):
            return WARN, self.FUTURE_SAMPLE_DATE

        return OK
