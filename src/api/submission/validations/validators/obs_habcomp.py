from ....models import HabitatComplexityScore
from ..utils import valid_id
from .base import ERROR, OK, BaseValidator, validate_list, validator_result


def valid_scores():
    return [str(pk) for pk in HabitatComplexityScore.objects.values_list("id", flat=True)]


class ScoreValidator(BaseValidator):
    INVALID_SCORE = "invalid_score"

    def __init__(self, score_path, **kwargs):
        self.score_path = score_path
        if "valid_scores" in kwargs:
            self.valid_scores = kwargs["valid_scores"]
        else:
            self.valid_scores = valid_scores()
        super().__init__(**kwargs)

    @validator_result
    def __call__(self, collect_record, **kwargs):
        score = valid_id(self.get_value(collect_record, self.score_path))

        if score not in self.valid_scores:
            return ERROR, self.INVALID_SCORE

        return OK


class ListScoreValidator(BaseValidator):
    INVALID_SCORE = "invalid_score"

    def __init__(self, observations_path, score_path, **kwargs):
        self.observations_path = observations_path
        self.score_path = score_path
        super().__init__(**kwargs)

    @validate_list
    def __call__(self, collect_record, **kwargs):
        observations = self.get_value(collect_record, self.observations_path) or []
        validator = ScoreValidator(self.score_path, valid_scores=valid_scores())
        return validator, observations
