import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import List, Tuple

import requests

from .base import BaseCovariate, CovariateRequestError


class CoralAtlasCovariate(BaseCovariate):
    api_url = "https://allencoralatlas.org"
    num_threads = 3
    BENTHIC_CLASS_TYPE = "benthic"
    GEOMORPHIC_CLASS_TYPE = "geomorphic"

    def _sqkm_to_sqm(self, area: float) -> float:
        return area * 1000000

    def _parse_classes(self, classes: List[dict]) -> List[dict]:
        classes = classes or []
        _classes = []
        for _class in classes:
            cover_m2 = self._sqkm_to_sqm(_class["cover_sqkm"])
            _classes.append(dict(name=_class["class_name"], area=cover_m2))

        return sorted(_classes, key=lambda x: (x["area"], x["name"]), reverse=True)

    def _fetch(
        self, x: float, y: float, radius: float, request_datetime: datetime
    ) -> dict:
        url = f"{self.api_url}/mapping/querypoint/{y}/{x}?radius={radius}"
        resp = requests.get(url)
        status_code = resp.status_code
        if status_code != 200:
            print(f"url={url}")
            raise CovariateRequestError(resp.text)

        data = (resp.json() or {}).get("data")
        stats = (data or {}).get("stats")
        map_assets = (stats or {}).get("map_assets") or []
        output = {"aca_benthic": [], "aca_geomorphic": []}
        for map_asset in map_assets:
            class_type = (map_asset.get("class_type") or "").lower()
            if not class_type or class_type not in (
                self.BENTHIC_CLASS_TYPE,
                self.GEOMORPHIC_CLASS_TYPE,
            ):
                continue
            classes = self._parse_classes(map_asset.get("classes"))
            output[f"aca_{class_type}"].extend(classes)

        return dict(
            date=request_datetime,
            requested_date=request_datetime,
            covariates=output,
        )

    def fetch(self, points: List[Tuple[float, float]]) -> List[dict]:
        futures = []
        response = []
        request_datetime = datetime.datetime.utcnow()
        with ThreadPoolExecutor(max_workers=self.num_threads) as exc:
            for point in points:
                x, y = point
                futures.append(
                    exc.submit(
                        self._fetch,
                        x=x,
                        y=y,
                        radius=self.radius,
                        request_datetime=request_datetime,
                    )
                )

            for future in futures:
                response.append(future.result())

        return response
