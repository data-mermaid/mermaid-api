from rest_framework.exceptions import ParseError

from ....exceptions import check_uuid
from ....models import Management
from .base import ERROR, OK, WARN, BaseValidator, validator_result


class UniqueManagementValidator(BaseValidator):
    MANAGEMENT_NOT_FOUND = "management_not_found"
    NOT_UNIQUE = "not_unique_management"
    name_match_percent = 0.5

    def __init__(self, management_path, **kwargs):
        self.management_path = management_path
        super().__init__(**kwargs)

    @validator_result
    def __call__(self, collect_record, **kwargs):
        management_id = self.get_value(collect_record, self.management_path) or ""
        try:
            check_uuid(management_id)
            management = Management.objects.get_or_none(id=management_id)
        except ParseError:
            management = None

        if management is None:
            return ERROR, self.MANAGEMENT_NOT_FOUND

        project_id = management.project_id
        name = management.name

        # Finds MRs that:
        # - are not self and in same project, and fuzzy match name, AND
        # - belong to SEs with the same site (but diff MR) as any SE with
        #   associated SUs that uses this MR OR
        # - belong to CRs with the same site (but diff MR) as any CR that uses this MR
        # When we make MR a FK of site, this can be replaced with simple ORM site lookup
        match_sql = """
            WITH se_mrs AS (
                SELECT DISTINCT management_id, site_id FROM
                sample_event ses
                INNER JOIN management ON (ses.management_id = management.id)
                LEFT JOIN transect_benthic tbs ON (ses.id = tbs.sample_event_id)
                LEFT JOIN transect_belt_fish tbfs ON (ses.id = tbfs.sample_event_id)
                LEFT JOIN quadrat_collection qcs ON (ses.id = qcs.sample_event_id)
                WHERE management.project_id = %(project_id)s
                AND (
                    tbs.id IS NOT NULL OR
                    tbfs.id IS NOT NULL OR
                    qcs.id IS NOT NULL
                )
            ),
            cr_mrs AS (
                SELECT DISTINCT (cr.data #>> '{sample_event, management}')::text AS "management_id",
                (cr.data #>> '{sample_event, site}')::text AS "site_id"
                FROM api_collectrecord cr
                WHERE cr.project_id = %(project_id)s
            ),
            se_diff_mrs AS (
                SELECT DISTINCT diffses.management_id FROM
                sample_event ses
                INNER JOIN sample_event diffses ON (ses.site_id = diffses.site_id)
                LEFT JOIN transect_benthic tbs ON (ses.id = tbs.sample_event_id)
                LEFT JOIN transect_belt_fish tbfs ON (ses.id = tbfs.sample_event_id)
                LEFT JOIN quadrat_collection qcs ON (ses.id = qcs.sample_event_id)
                LEFT JOIN transect_benthic tb ON (diffses.id = tb.sample_event_id)
                LEFT JOIN transect_belt_fish tbf ON (diffses.id = tbf.sample_event_id)
                LEFT JOIN quadrat_collection qc ON (diffses.id = qc.sample_event_id)
                WHERE ses.management_id = %(mr_id)s
                AND diffses.management_id != %(mr_id)s
                AND (
                    tb.id IS NOT NULL OR
                    tbf.id IS NOT NULL OR
                    qc.id IS NOT NULL
                )
                AND (
                    tbs.id IS NOT NULL OR
                    tbfs.id IS NOT NULL OR
                    qcs.id IS NOT NULL
                )
            ),
            cr_diff_mrs AS (
                SELECT DISTINCT (
                    diff_cr_mans.data #>> '{sample_event, management}')::text AS "management_id"
                FROM
                    api_collectrecord self_cr_mans
                INNER JOIN api_collectrecord diff_cr_mans ON (
                    (self_cr_mans.data #>> '{sample_event, site}') =
                    (diff_cr_mans.data #>> '{sample_event, site}')
                )
                WHERE (
                    (self_cr_mans.data #>> '{sample_event, management}')::text = %(mr_id)s AND
                    (diff_cr_mans.data #>> '{sample_event, management}')::text != %(mr_id)s
                )
            )
            SELECT management.id, management.project_id, management.name, management.name_secondary,
            SIMILARITY(management.name, %(name)s) AS "similarity"
            FROM management
            WHERE (
                NOT (management.id = %(mr_id)s)
                AND management.project_id = %(project_id)s
                AND SIMILARITY(management.name, %(name)s) >= %(match_percent)s
                AND (
                    management.id IN (SELECT * FROM se_diff_mrs)
                    OR management.id::text IN (SELECT * FROM cr_diff_mrs)
                    OR management.id IN (SELECT * FROM (
                        SELECT CASE
                        WHEN se_mrs.management_id != %(mr_id)s THEN se_mrs.management_id
                        WHEN cr_mrs.management_id::text != %(mr_id)s THEN cr_mrs.management_id::uuid
                        END
                        FROM se_mrs
                        INNER JOIN cr_mrs ON (se_mrs.site_id::text = cr_mrs.site_id)
                        WHERE (
                            se_mrs.management_id = %(mr_id)s AND
                            cr_mrs.management_id != %(mr_id)s
                        ) OR
                        (cr_mrs.management_id = %(mr_id)s AND se_mrs.management_id != %(mr_id)s)
                    ) AS se_cr)
                )
            )
            ORDER BY similarity DESC
        """
        params = {
            "mr_id": str(management_id),
            "project_id": str(project_id),
            "name": name,
            "match_percent": self.name_match_percent,
        }

        qry = Management.objects.raw(match_sql, params)
        results = qry[0:3]
        if len(results) > 0:
            matches = [str(r.id) for r in results]
            return WARN, self.NOT_UNIQUE, {"matches": dict(matches=matches)}

        return OK


class ManagementRuleValidator(BaseValidator):
    REQUIRED_RULES = "required_management_rules"

    def __init__(self, management_path):
        self.management_path = management_path

    @validator_result
    def __call__(self, collect_record, **kwargs):
        management_id = self.get_value(collect_record, self.management_path) or None

        management = Management.objects.get_or_none(id=management_id)
        if not management or not management.rules:
            return ERROR, self.REQUIRED_RULES

        return OK
