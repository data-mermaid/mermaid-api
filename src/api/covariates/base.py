class CovariateRequestError(Exception):
    pass


class BaseCovariate:
    def __init__(self, *args, **kwargs):
        self.radius = kwargs.get("radius") or 0.025  # in km

    def fetch(self, points: list[tuple[float, float]]) -> list[dict]:
        raise NotImplementedError()
