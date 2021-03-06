from django.utils.translation import ugettext_lazy as _

from .validations import (
    ERROR,
    OK,
    WARN,
    BenthicTransectValidation,
    EmptyListValidation,
    FishBeltTransectValidation,
    ManagementValidation,
    ObsBenthicLITValidation,
    ObsBenthicPercentCoveredValidation,
    ObsBenthicPITValidation,
    ObsColoniesBleachedValidation,
    ObservationsValidation,
    ObsFishBeltValidation,
    ObsHabitatComplexitiesValidation,
    QuadratCollectionValidation,
    SampleEventValidation,
    SerializerValidation,
    SiteValidation,
    ValueInRangeValidation,
)


class ProtocolValidation(object):
    def __init__(self, collect_record, request=None):
        self.status = None
        self.collect_record = collect_record
        self.request = request
        self.validations = dict()

    def _run_validation(self, validation_cls, *args, **kwargs):
        validation = validation_cls(*args, **kwargs)
        if (
            self.collect_record.validations
            and "results" in self.collect_record.validations
        ):
            prev_validations = self.collect_record.validations["results"]
        else:
            prev_validations = dict()

        validation.previous_validations = prev_validations.get(
            validation.identifier, dict()
        )
        result = validation.validate()
        for k, v in validation.logs.items():
            if k not in self.validations:
                self.validations[k] = dict()

            self.validations[k].update(v)
        return result

    def validate(self):
        results = []
        self.validations = dict()

        data = self.collect_record.data or dict()
        sample_event_data = data.get("sample_event") or dict()
        observers = data.get("observers") or []
        site_id = sample_event_data.get("site")
        management_id = sample_event_data.get("management")
        # depth = sample_event_data.get("depth")

        results.append(self._run_validation(SampleEventValidation, data))
        results.append(self._run_validation(SiteValidation, site_id))

        results.append(self._run_validation(ManagementValidation, management_id))

        results.append(
            self._run_validation(
                EmptyListValidation,
                "observers",
                observers,
                str(_("Must have at least 1 observer")),
            )
        )

        results.append(self._run_validation(ObservationsValidation, data))

        # results.append(
        #     self._run_validation(
        #         ValueInRangeValidation,
        #         "depth",
        #         depth,
        #         self.DEPTH_RANGE,
        #         status=WARN,
        #         message=self.DEPTH_MSG,
        #         value_range_operators=("<", ">"),
        #     )
        # )

        serializer_validation = SerializerValidation(self.collect_record, self.request)
        serializer_validation.previous_validations = dict()
        results.append(serializer_validation.validate())

        for identifier, value in serializer_validation.logs.items():
            if identifier not in self.validations:
                self.validations[identifier] = dict()
            self.validations[identifier].update(value)

        if ERROR in results:
            return ERROR

        elif WARN in results:
            return WARN

        elif len(results) == results.count(OK):
            return OK

        raise ValueError(str(_("Validation result can not be determined.")))


class SampleUnitValidation(ProtocolValidation):
    DEPTH_RANGE = (1, 30)
    DEPTH_MSG = str(_("Depth value outside range of {} and {}".format(*DEPTH_RANGE)))

    def validate(self):
        results = []
        results.append(super(SampleUnitValidation, self).validate())

        data = self.collect_record.data or dict()
        sample_unit = data.get(self.SAMPLE_UNIT) or dict()
        depth = sample_unit.get("depth")

        results.append(
            self._run_validation(
                ValueInRangeValidation,
                "depth",
                depth,
                self.DEPTH_RANGE,
                status=WARN,
                message=self.DEPTH_MSG,
                value_range_operators=("<", ">"),
            )
        )

        if ERROR in results:
            return ERROR

        elif WARN in results:
            return WARN

        elif len(results) == results.count(OK):
            return OK


class TransectValidation(SampleUnitValidation):
    LENGTH_RANGE = (10, 100)
    LENGTH_RANGE_WARN_MSG_TMPL = (
        "Transect length surveyed value " + "outside range of {} and {}"
    )
    SAMPLE_UNIT = None

    def validate(self):
        results = [super(TransectValidation, self).validate()]

        data = self.collect_record.data or dict()

        if self.SAMPLE_UNIT is None:
            raise NotImplementedError(f"{SAMPLE_UNIT} not defined")

        sample_unit = data.get(self.SAMPLE_UNIT) or dict()
        len_surveyed = sample_unit.get("len_surveyed")
        results.append(
            self._run_validation(
                ValueInRangeValidation,
                "len_surveyed",
                len_surveyed,
                self.LENGTH_RANGE,
                WARN,
                str(_(self.LENGTH_RANGE_WARN_MSG_TMPL.format(*self.LENGTH_RANGE))),
            )
        )

        if ERROR in results:
            return ERROR

        elif WARN in results:
            return WARN

        elif len(results) == results.count(OK):
            return OK


class QuadratValidation(SampleUnitValidation):
    SAMPLE_UNIT = "quadrat_collection"

    def validate(self):
        results = [super(QuadratValidation, self).validate()]
        data = self.collect_record.data

        quadrat_collection = data.get("quadrat_collection") or dict()
        quadrat_size = quadrat_collection.get("quadrat_size")

        results.append(
            self._run_validation(
                ValueInRangeValidation,
                "quadrat_size",
                quadrat_size,
                value_range=(0,),
                value_range_operators=("<=",),
                message=_("Quadrat size must be greater than 0"),
            )
        )

        if ERROR in results:
            return ERROR

        elif WARN in results:
            return WARN

        elif len(results) == results.count(OK):
            return OK


class FishBeltProtocolValidation(TransectValidation):
    LENGTH_RANGE = (25, 100)
    SAMPLE_UNIT = "fishbelt_transect"

    def validate(self):
        results = [super(FishBeltProtocolValidation, self).validate()]

        data = self.collect_record.data or dict()

        results.append(self._run_validation(FishBeltTransectValidation, data))
        results.append(self._run_validation(ObsFishBeltValidation, data))

        if ERROR in results:
            return ERROR

        elif WARN in results:
            return WARN

        elif len(results) == results.count(OK):
            return OK


class BenthicPITProtocolValidation(TransectValidation):
    SAMPLE_UNIT = "benthic_transect"

    def validate(self):
        results = [super(BenthicPITProtocolValidation, self).validate()]

        data = self.collect_record.data or dict()
        results.append(self._run_validation(BenthicTransectValidation, data))
        results.append(self._run_validation(ObsBenthicPITValidation, data))

        if ERROR in results:
            return ERROR

        elif WARN in results:
            return WARN

        elif len(results) == results.count(OK):
            return OK


class BenthicLITProtocolValidation(TransectValidation):
    SAMPLE_UNIT = "benthic_transect"
    LENGTH_RANGE = (10, 100)

    def validate(self):
        results = [super(BenthicLITProtocolValidation, self).validate()]

        data = self.collect_record.data or dict()
        results.append(self._run_validation(BenthicTransectValidation, data))
        results.append(self._run_validation(ObsBenthicLITValidation, data))

        if ERROR in results:
            return ERROR

        elif WARN in results:
            return WARN

        elif len(results) == results.count(OK):
            return OK


class HabitatComplexityProtocolValidation(TransectValidation):
    SAMPLE_UNIT = "benthic_transect"

    def validate(self):
        results = [super(HabitatComplexityProtocolValidation, self).validate()]

        data = self.collect_record.data or dict()
        results.append(self._run_validation(BenthicTransectValidation, data))
        results.append(self._run_validation(ObsHabitatComplexitiesValidation, data))

        if ERROR in results:
            return ERROR

        elif WARN in results:
            return WARN

        elif len(results) == results.count(OK):
            return OK


class BleachingQuadratCollectionProtocolValidation(QuadratValidation):
    def validate(self):
        results = [super(BleachingQuadratCollectionProtocolValidation, self).validate()]

        data = self.collect_record.data or dict()

        results.append(self._run_validation(QuadratCollectionValidation, data))
        results.append(self._run_validation(ObsBenthicPercentCoveredValidation, data))
        results.append(self._run_validation(ObsColoniesBleachedValidation, data))

        if ERROR in results:
            return ERROR

        elif WARN in results:
            return WARN

        elif len(results) == results.count(OK):
            return OK
