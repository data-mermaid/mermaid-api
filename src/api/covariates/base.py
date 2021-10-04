from typing import List, Tuple


class CovariateRequestError(Exception):
    pass


class BaseCovariate:
    radius = 0.025  # in km

    def fetch(self, points: List[Tuple[float, float]]) -> List[dict]:
        raise NotImplementedError()
