import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import List, Tuple

from django.db import connection

from .base import BaseCovariate


class VibrantOceansThreatsCovariate(BaseCovariate):
    num_threads = 3

    SCORE = "score"
    SCORE_CN = "scorecn"
    SCORE_CY = "scorecy"
    SCORE_PFC = "scorepfc"
    SCORE_TH = "scoreth"
    SCORE_TR = "scoretr"
    GRAV_NC = "grav_nc_raw"
    SEDIMENT = "sediment_raw"
    NUTRIENT = "nutrient_raw"
    POP_COUNT = "pop_count_raw"
    NUM_PORTS = "num_ports_raw"
    REEF_VALUE = "reef_value_raw"
    CUMUL_SCORE = "cumul_score"

    COLUMNS = (
        SCORE,
        SCORE_CN,
        SCORE_CY,
        SCORE_PFC,
        SCORE_TH,
        SCORE_TR,
        GRAV_NC,
        SEDIMENT,
        NUTRIENT,
        POP_COUNT,
        NUM_PORTS,
        REEF_VALUE,
        CUMUL_SCORE,
    )

    def _table_exists(self):
        sql = """
            SELECT EXISTS (
                SELECT 1
                FROM
                    information_schema.tables
                WHERE
                    table_schema = 'covariates' AND
                    table_name = 'allreef'
            )
        """
        with connection.cursor() as cursor:
            cursor.execute(sql)
            record = cursor.fetchone()
            return record[0]

    def _fetch(self, x: float, y: float, radius: float, request_datetime: datetime):
        if self._table_exists() is not True:
            return None

        _covariate_cols = ", ".join(self.COLUMNS)
        _sum_covariate_cols = ", ".join(f"SUM({c} * partial) as {c}" for c in self.COLUMNS)
        sql_template = f"""
            WITH allreef_clipped AS (
                SELECT
                    {_covariate_cols},
                    ST_Area(
                        ST_Intersection(
                            ST_Buffer(ST_GeomFromText('SRID=4326;POINT(%(x)s %(y)s)')::geography,%(radius)s),
                            allreef.geom::geography
                        ),
                        true
                    ) /
                    ST_Area(
                        ST_Buffer(ST_GeomFromText('SRID=4326;POINT(%(x)s %(y)s)')::geography,%(radius)s),
                        true
                    ) as partial
                FROM "covariates"."allreef" AS allreef
                WHERE
                    ST_Intersects(
                        ST_Buffer(ST_GeomFromText('SRID=4326;POINT(%(x)s %(y)s)')::geography, %(radius)s),
                        allreef.geom::geography
                    )
            )
            SELECT
                {_sum_covariate_cols}
            FROM
                allreef_clipped
        """

        output = {col: None for col in self.COLUMNS}

        with connection.cursor() as cursor:
            params = {"x": x, "y": y, "radius": radius * 1000}
            cursor.execute(sql_template, params=params)
            record = cursor.fetchone()

            if record is None:
                return output

            output = {col: record[i] for i, col in enumerate(self.COLUMNS)}

        return {
            "date": request_datetime,
            "requested_date": request_datetime,
            "covariates": output,
        }

    def fetch(self, points: List[Tuple[float, float]]) -> List[dict]:
        futures = []
        results = []
        request_datetime = datetime.datetime.now(datetime.UTC)
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
                results.append(future.result())

        return results
