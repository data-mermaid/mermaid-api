from collections import defaultdict
from django.core.validators import MaxValueValidator
from .base import OK, WARN, ERROR, BaseValidator, validator_result
from ....models.mermaid import QuadratTransect


class PointsPerQuadratValidator(BaseValidator):
    INVALID_NUMBER_POINTS = "invalid_number_of_points"

    def __init__(
        self,
        num_points_per_quadrat_path,
        obs_benthic_photo_quadrats_path,
        observation_quadrat_number_path,
        observation_num_points_path,
        **kwargs,
    ):
        self.num_points_per_quadrat_path = num_points_per_quadrat_path
        self.obs_benthic_photo_quadrats_path = obs_benthic_photo_quadrats_path
        self.observation_quadrat_number_path = observation_quadrat_number_path
        self.observation_num_points_path = observation_num_points_path
        super().__init__(**kwargs)

    @validator_result
    def __call__(self, collect_record, **kwargs):
        num_points_per_quadrat = self.get_value(
            collect_record, self.num_points_per_quadrat_path
        )
        observations = (
            self.get_value(collect_record, self.obs_benthic_photo_quadrats_path) or []
        )

        quadrat_number_groups = defaultdict(int)
        for obs in observations:
            quadrat_number = self.get_value(obs, self.observation_quadrat_number_path)
            try:
                num_points = self.get_value(obs, self.observation_num_points_path) or 0
            except (TypeError, ValueError):
                continue

            if quadrat_number is None:
                continue
            quadrat_number_groups[quadrat_number] += num_points

        invalid_quadrat_numbers = []
        for qn, pnt_cnt in quadrat_number_groups.items():
            if pnt_cnt != num_points_per_quadrat:
                invalid_quadrat_numbers.append(qn)

        if len(invalid_quadrat_numbers) > 0:
            return (
                WARN,
                self.INVALID_NUMBER_POINTS,
                {"invalid_quadrat_numbers": invalid_quadrat_numbers},
            )

        return OK


class QuadratCountValidator(BaseValidator):
    DIFFERENT_NUMBER_OF_QUADRATS = "diff_num_quadrats"

    def __init__(
        self,
        num_quadrats_path,
        obs_benthic_photo_quadrats_path,
        observation_quadrat_number_path,
        **kwargs,
    ):
        self.num_quadrats_path = num_quadrats_path
        self.obs_benthic_photo_quadrats_path = obs_benthic_photo_quadrats_path
        self.observation_quadrat_number_path = observation_quadrat_number_path

        super().__init__(**kwargs)

    @validator_result
    def __call__(self, collect_record, **kwargs):
        num_quadrats = self.get_value(collect_record, self.num_quadrats_path)
        observations = (
            self.get_value(collect_record, self.obs_benthic_photo_quadrats_path) or []
        )
        quadrat_numbers = {
            self.get_value(o, self.observation_quadrat_number_path)
            for o in observations
        }

        if len(quadrat_numbers) != num_quadrats:
            return WARN, self.DIFFERENT_NUMBER_OF_QUADRATS

        return OK


class QuadratNumberSequenceValidator(BaseValidator):
    LARGE_NUM_QUADRATS = "large_num_quadrats"
    MISSING_QUADRAT_NUMBERS = "missing_quadrat_numbers"

    def __init__(
        self,
        num_quadrats_path,
        obs_benthic_photo_quadrats_path,
        observation_quadrat_number_path,
        quadrat_number_start_path,
        **kwargs,
    ):
        self.num_quadrats_path = num_quadrats_path
        self.obs_benthic_photo_quadrats_path = obs_benthic_photo_quadrats_path
        self.observation_quadrat_number_path = observation_quadrat_number_path
        self.quadrat_number_start_path = quadrat_number_start_path

        super().__init__(**kwargs)

    @validator_result
    def __call__(self, collect_record, **kwargs):
        num_quadrats_max = 10000  # default max for num_quadrats
        for validator in QuadratTransect.num_quadrats.field.validators:
            if isinstance(validator, MaxValueValidator):
                num_quadrats_max = validator.limit_value

        num_quadrats = self.get_value(collect_record, self.num_quadrats_path) or 0
        # bail out early if num_quadrats will cause list(range()) below to crash server
        if num_quadrats > num_quadrats_max:
            return ERROR, self.LARGE_NUM_QUADRATS, {"max_value": num_quadrats_max}

        observations = (
            self.get_value(collect_record, self.obs_benthic_photo_quadrats_path) or []
        )
        quadrat_number_start = (
            self.get_value(collect_record, self.quadrat_number_start_path) or 1
        )
        quadrat_numbers = []
        for o in observations:
            quadrat_number = self.get_value(o, self.observation_quadrat_number_path)
            if quadrat_number is None:
                continue
            quadrat_numbers.append(quadrat_number)
        quadrat_numbers = set(quadrat_numbers)

        quadrat_number_seq = [
            i for i in range(quadrat_number_start, quadrat_number_start + num_quadrats)
        ]

        missing_quadrat_numbers = [
            qn for qn in quadrat_number_seq if qn not in quadrat_numbers
        ]

        if missing_quadrat_numbers:
            return (
                WARN,
                self.MISSING_QUADRAT_NUMBERS,
                {"missing_quadrat_numbers": missing_quadrat_numbers},
            )

        return OK
