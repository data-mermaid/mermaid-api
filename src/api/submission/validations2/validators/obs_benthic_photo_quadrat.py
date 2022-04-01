from collections import defaultdict
from dataclasses import MISSING
from .base import OK, WARN, ERROR, BaseValidator, validator_result


class PointsPerQuadratValidator(BaseValidator):
    INVALID_NUMBER_POINTS = "invalid_number_of_points"

    def __init__(
        self,
        num_points_per_quadrat_path,
        obs_benthic_photo_quadrats_path,
        observation_quadrat_number_path,
        observation_num_points_path,
        **kwargs
    ):
        self.num_points_per_quadrat_path = num_points_per_quadrat_path
        self.obs_benthic_photo_quadrats_path = obs_benthic_photo_quadrats_path
        self.observation_quadrat_number_path = observation_quadrat_number_path
        self.observation_num_points_path = observation_num_points_path
        super().__init__(**kwargs)

    @validator_result
    def __call__(self, collect_record, **kwargs):
        num_points_per_quadrat = self.get_value(collect_record, self.num_points_per_quadrat_path)
        observations = self.get_value(collect_record, self.obs_benthic_photo_quadrats_path) or []

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
            return WARN, self.INVALID_NUMBER_POINTS, {"invalid_quadrat_numbers": invalid_quadrat_numbers}

        return OK



class QuadratCountValidator(BaseValidator):
    DIFFERENT_NUMBER_OF_QUADRATS = "diff_num_quadrats"

    def __init__(
        self,
        num_quadrats_path,
        obs_benthic_photo_quadrats_path,
        observation_quadrat_number_path,
        **kwargs
    ):
        self.num_quadrats_path = num_quadrats_path
        self.obs_benthic_photo_quadrats_path = obs_benthic_photo_quadrats_path
        self.observation_quadrat_number_path = observation_quadrat_number_path

        super().__init__(**kwargs)
    
    @validator_result
    def __call__(self, collect_record, **kwargs):
        num_quadrats = self.get_value(collect_record, self.num_quadrats_path)
        observations = self.get_value(collect_record, self.obs_benthic_photo_quadrats_path) or []
        quadrat_numbers = {self.get_value(o, self.observation_quadrat_number_path) for o in observations}

        if len(quadrat_numbers) != num_quadrats:
            return WARN, self.DIFFERENT_NUMBER_OF_QUADRATS

        return OK


class QuadratNumberSequenceValidator(BaseValidator):
    MISSING_QUADRAT_NUMBERS = "missing_quadrat_numbers"

    def __init__(
        self,
        num_quadrats_path,
        obs_benthic_photo_quadrats_path,
        observation_quadrat_number_path,
        **kwargs
    ):
        self.num_quadrats_path = num_quadrats_path
        self.obs_benthic_photo_quadrats_path = obs_benthic_photo_quadrats_path
        self.observation_quadrat_number_path = observation_quadrat_number_path

        super().__init__(**kwargs)
    
    @validator_result
    def __call__(self, collect_record, **kwargs):
        num_quadrats = self.get_value(collect_record, self.num_quadrats_path)
        observations = self.get_value(collect_record, self.obs_benthic_photo_quadrats_path) or []
        quadrat_numbers = sorted({self.get_value(o, self.observation_quadrat_number_path) for o in observations})

        quadrat_number_seq = [quadrat_numbers[0] + i for i in range(len(quadrat_numbers))]

        missing_quadrat_numbers = [qn for qn in quadrat_number_seq if qn not in quadrat_numbers]
        
        if missing_quadrat_numbers:
            return WARN, self.MISSING_QUADRAT_NUMBERS, {"missing_quadrat_numbers": missing_quadrat_numbers}

        print(f"quadrat_numbers: {quadrat_numbers}")

        return WARN


# class UniqueObsBenthicPhotoQuadrat(BaseValidator):
#     # "benthic_photo_quadrat_transect",
#     #         "quadrat_number",
#     #         "attribute",
#     #         "growth_form"
#     def __init__(
#         self,
#         obs_benthic_photo_quadrats_path,
#         observation_quadrat_number_path,
#         observation_attribute_path,
#         observation_growth_form_path,
#         **kwargs
#     ):
#         self.obs_benthic_photo_quadrats_path = obs_benthic_photo_quadrats_path
#         self.observation_quadrat_number_path = observation_quadrat_number_path
#         self.observation_attribute_path = observation_attribute_path
#         self.observation_growth_form_path = observation_growth_form_path
#         super().__init__(**kwargs)
    
#     def _create_key(self, obs):
#         quadrat_number = self.get_value(obs, self.observation_quadrat_number_path)
#         attribute = self.get_value(obs, self.observation_attribute_path)
#         growth_form = self.get_value(obs, self.observation_growth_form_path)
#         return f"{quadrat_number}::{attribute}::{growth_form}"

#     @validator_result
#     def __call__(self, collect_record, **kwargs):
#         observations = self.get_value(collect_record, self.obs_benthic_photo_quadrats_path) or []
#         groups = defaultdict(list)
#         for obs in observations:
#             key = self._create_key(obs)
#             groups[key].append(obs.get("id"))
        
#         duplicates = [group for group in groups if len(group) > 1]

#         return OK