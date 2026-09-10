"""
Validators for checking consistency of sample unit attributes within the same sample event.
"""

from django.utils.dateparse import parse_date

from ....models import (
    BENTHICLIT_PROTOCOL,
    BENTHICPIT_PROTOCOL,
    BENTHICPQT_PROTOCOL,
    FISHBELT_PROTOCOL,
    HABITATCOMPLEXITY_PROTOCOL,
    MACROINVERTEBRATE_PROTOCOL,
    BeltFish,
    BeltInvert,
    BenthicLIT,
    BenthicPhotoQuadratTransect,
    BenthicPIT,
    BleachingQuadratCollection,
    FishBeltTransect,
    HabitatComplexity,
    InvertBeltTransect,
    SampleEvent,
)
from ..statuses import OK, WARN
from ..utils import valid_id
from .base import BaseValidator, validator_result


class SampleEventConsistencyValidator(BaseValidator):
    def __init__(self, site_path, management_path, sample_date_path, **kwargs):
        self.site_path = site_path
        self.management_path = management_path
        self.sample_date_path = sample_date_path
        super().__init__(**kwargs)

    def _get_sample_event(self, collect_record):
        """
        Extract sample event identifiers and look up the sample event.
        Returns the sample_event if found, or None if validation should be skipped.
        """
        site_id = valid_id(self.get_value(collect_record, self.site_path))
        management_id = valid_id(self.get_value(collect_record, self.management_path))
        sample_date_str = self.get_value(collect_record, self.sample_date_path)

        if not site_id or not management_id or not sample_date_str:
            return None
        sample_date = parse_date(sample_date_str)
        if sample_date is None:
            return None  # Let other validators handle invalid dates

        cache = self.get_run_cache(collect_record, "sample_events")
        key = (str(site_id), str(management_id), sample_date)
        if key not in cache:
            cache[key] = SampleEvent.objects.filter(
                site_id=site_id,
                management_id=management_id,
                sample_date=sample_date,
            ).first()

        return cache[key]

    def _get_sibling_sample_units(
        self, collect_record, sample_event, model, sample_event_path, select_related=()
    ):
        """Sample units of one protocol already recorded against a sample event.

        A protocol can stack several of these checks against the same rows: BPQT
        compares num_quadrats, num_points_per_quadrat and len_surveyed, all of which
        live on the same quadrat_transect. Cache the rows for the validation run so
        they are fetched once rather than once per validator.
        """
        cache = self.get_run_cache(collect_record, "sibling_sample_units")
        key = (model, sample_event_path, str(sample_event.pk), select_related)
        if key not in cache:
            queryset = model.objects.filter(**{sample_event_path: sample_event})
            if select_related:
                queryset = queryset.select_related(*select_related)
            cache[key] = list(queryset)

        return cache[key]


class DifferentNumQuadratsValidator(SampleEventConsistencyValidator):
    """
    Validates that the number of quadrats in a PQT sample unit matches that of other PQT sample units
    in the same sample event.
    """

    DIFFERENT_NUM_QUADRATS = "different_num_quadrats_se"

    def __init__(self, site_path, management_path, sample_date_path, num_quadrats_path, **kwargs):
        super().__init__(site_path, management_path, sample_date_path, **kwargs)
        self.num_quadrats_path = num_quadrats_path

    @validator_result
    def __call__(self, collect_record, **kwargs):
        sample_event = self._get_sample_event(collect_record)
        num_quadrats = self.get_numeric_value(collect_record, self.num_quadrats_path)
        if not sample_event or not num_quadrats:
            return OK

        for pqt_su in self._get_sibling_sample_units(
            collect_record,
            sample_event,
            BenthicPhotoQuadratTransect,
            "quadrat_transect__sample_event",
            ("quadrat_transect",),
        ):
            other_num_quadrats = pqt_su.quadrat_transect.num_quadrats
            if other_num_quadrats != num_quadrats:
                return (
                    WARN,
                    self.DIFFERENT_NUM_QUADRATS,
                    {
                        "num_quadrats": num_quadrats,
                        "other_num_quadrats": other_num_quadrats,
                    },
                )

        return OK


class DifferentNumPointsPerQuadratValidator(SampleEventConsistencyValidator):
    """
    Validates that the number of points per quadrat in a PQT sample unit matches that of other PQT
    sample units in the same sample event.
    """

    DIFFERENT_NUM_POINTS_PER_QUADRAT = "different_num_points_per_quadrat_se"

    def __init__(
        self,
        site_path,
        management_path,
        sample_date_path,
        num_points_per_quadrat_path,
        **kwargs,
    ):
        super().__init__(site_path, management_path, sample_date_path, **kwargs)
        self.num_points_per_quadrat_path = num_points_per_quadrat_path

    @validator_result
    def __call__(self, collect_record, **kwargs):
        sample_event = self._get_sample_event(collect_record)
        num_points_per_quadrat = self.get_numeric_value(
            collect_record, self.num_points_per_quadrat_path
        )
        if not sample_event or not num_points_per_quadrat:
            return OK

        for pqt_su in self._get_sibling_sample_units(
            collect_record,
            sample_event,
            BenthicPhotoQuadratTransect,
            "quadrat_transect__sample_event",
            ("quadrat_transect",),
        ):
            other_num_points_per_quadrat = pqt_su.quadrat_transect.num_points_per_quadrat
            if other_num_points_per_quadrat != num_points_per_quadrat:
                return (
                    WARN,
                    self.DIFFERENT_NUM_POINTS_PER_QUADRAT,
                    {
                        "num_points_per_quadrat": num_points_per_quadrat,
                        "other_num_points_per_quadrat": other_num_points_per_quadrat,
                    },
                )

        return OK


class DifferentTransectWidthValidator(SampleEventConsistencyValidator):
    """
    Validates that the transect width in a fish belt sample unit matches that of other fish belt
    sample units in the same sample event.
    """

    DIFFERENT_TRANSECT_WIDTH = "different_transect_width_se"

    def __init__(self, site_path, management_path, sample_date_path, width_path, **kwargs):
        super().__init__(site_path, management_path, sample_date_path, **kwargs)
        self.width_path = width_path

    @validator_result
    def __call__(self, collect_record, **kwargs):
        sample_event = self._get_sample_event(collect_record)
        width_id = valid_id(self.get_value(collect_record, self.width_path))
        if not sample_event or not width_id:
            return OK

        for fb_su in self._get_sibling_sample_units(
            collect_record, sample_event, FishBeltTransect, "sample_event"
        ):
            other_width_id = valid_id(fb_su.width_id)
            if other_width_id:
                other_width_id = str(other_width_id)
                width_id = str(width_id)

                if other_width_id != width_id:
                    return (
                        WARN,
                        self.DIFFERENT_TRANSECT_WIDTH,
                        {
                            "width": width_id,
                            "other_width": other_width_id,
                        },
                    )

        return OK


class DifferentInvertTransectWidthValidator(SampleEventConsistencyValidator):
    """
    Validates that the transect width in a macroinvertebrate belt sample unit matches that of other
    macroinvertebrate belt sample units in the same sample event.
    """

    DIFFERENT_TRANSECT_WIDTH = "different_transect_width_se"

    def __init__(self, site_path, management_path, sample_date_path, width_path, **kwargs):
        super().__init__(site_path, management_path, sample_date_path, **kwargs)
        self.width_path = width_path

    @validator_result
    def __call__(self, collect_record, **kwargs):
        sample_event = self._get_sample_event(collect_record)
        width_id = valid_id(self.get_value(collect_record, self.width_path))
        if not sample_event or not width_id:
            return OK

        width_id = str(width_id)
        for su in self._get_sibling_sample_units(
            collect_record, sample_event, InvertBeltTransect, "sample_event"
        ):
            other_width_id = valid_id(su.width_id)
            if other_width_id:
                if str(other_width_id) != width_id:
                    return (
                        WARN,
                        self.DIFFERENT_TRANSECT_WIDTH,
                        {
                            "width": width_id,
                            "other_width": str(other_width_id),
                        },
                    )

        return OK


class DifferentTransectLengthValidator(SampleEventConsistencyValidator):
    """
    Validates that the transect length in a transect-based sample unit matches that of other sample
    units of the same protocol in the same sample event.
    """

    DIFFERENT_TRANSECT_LENGTH = "different_transect_length_se"

    # Map of protocol to (model, sample_event_path) tuples
    PROTOCOL_CONFIG = {
        BENTHICLIT_PROTOCOL: (BenthicLIT, "transect__sample_event"),
        BENTHICPIT_PROTOCOL: (BenthicPIT, "transect__sample_event"),
        BENTHICPQT_PROTOCOL: (BenthicPhotoQuadratTransect, "quadrat_transect__sample_event"),
        FISHBELT_PROTOCOL: (BeltFish, "transect__sample_event"),
        HABITATCOMPLEXITY_PROTOCOL: (HabitatComplexity, "transect__sample_event"),
        MACROINVERTEBRATE_PROTOCOL: (BeltInvert, "transect__sample_event"),
    }

    def __init__(
        self,
        protocol_path,
        site_path,
        management_path,
        sample_date_path,
        len_surveyed_path,
        **kwargs,
    ):
        super().__init__(site_path, management_path, sample_date_path, **kwargs)
        self.protocol_path = protocol_path
        self.len_surveyed_path = len_surveyed_path

    @validator_result
    def __call__(self, collect_record, **kwargs):
        sample_event = self._get_sample_event(collect_record)
        protocol = self.get_value(collect_record, self.protocol_path)
        len_surveyed = self.get_numeric_value(collect_record, self.len_surveyed_path)

        if (
            not sample_event
            or not protocol
            or not len_surveyed
            or protocol not in self.PROTOCOL_CONFIG
        ):
            return OK

        model, sample_event_path = self.PROTOCOL_CONFIG[protocol]
        su_str = sample_event_path.split("__")[0]  # transect or quadrat_transect

        for method in self._get_sibling_sample_units(
            collect_record, sample_event, model, sample_event_path, (su_str,)
        ):
            su = getattr(method, su_str)
            other_len_surveyed = su.len_surveyed

            if other_len_surveyed is not None and other_len_surveyed != len_surveyed:
                return (
                    WARN,
                    self.DIFFERENT_TRANSECT_LENGTH,
                    {
                        "protocol": protocol,
                        "len_surveyed": float(len_surveyed),
                        "other_len_surveyed": float(other_len_surveyed),
                    },
                )

        return OK


class DifferentQuadratSizeValidator(SampleEventConsistencyValidator):
    """
    Validates that the quadrat size in a bleaching quadrat collection sample unit matches that of
    other bleaching quadrat collection sample units in the same sample event.
    """

    DIFFERENT_QUADRAT_SIZE = "different_quadrat_size_se"

    def __init__(self, site_path, management_path, sample_date_path, quadrat_size_path, **kwargs):
        super().__init__(site_path, management_path, sample_date_path, **kwargs)
        self.quadrat_size_path = quadrat_size_path

    @validator_result
    def __call__(self, collect_record, **kwargs):
        sample_event = self._get_sample_event(collect_record)
        quadrat_size = self.get_numeric_value(collect_record, self.quadrat_size_path)
        if not sample_event or not quadrat_size:
            return OK

        for bqc_su in self._get_sibling_sample_units(
            collect_record,
            sample_event,
            BleachingQuadratCollection,
            "quadrat__sample_event",
            ("quadrat",),
        ):
            other_quadrat_size = bqc_su.quadrat.quadrat_size
            if other_quadrat_size != quadrat_size:
                return (
                    WARN,
                    self.DIFFERENT_QUADRAT_SIZE,
                    {
                        "quadrat_size": float(quadrat_size),
                        "other_quadrat_size": float(other_quadrat_size),
                    },
                )

        return OK
