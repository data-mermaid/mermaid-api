from rest_framework.exceptions import ParseError

from ....exceptions import check_uuid
from ....models import Management, Site
from .base import ERROR, OK, WARN, BaseValidator, validator_result


class UniqueManagementValidator(BaseValidator):
    MANAGEMENT_NOT_FOUND = "management_not_found"
    SITE_NOT_FOUND = "site_not_found"
    NOT_UNIQUE = "not_unique_management"
    SIMILAR_NAME = "similar_name"

    def __init__(self, management_path, site_path, **kwargs):
        self.management_path = management_path
        self.site_path = site_path
        super().__init__(**kwargs)

    def _duplicate_by_site(self, project_id, management_id, site_id):
        # Finds MRs that:
        # - are not self and in same project,
        # - AND belong to SEs with the same site (but diff MR) as any SE with
        # associated SUs that uses this MR
        match_sql = """
            WITH se_mrs AS (
                SELECT DISTINCT management_id, site_id FROM
                sample_event ses
                INNER JOIN management ON (ses.management_id = management.id)
                LEFT JOIN transect_benthic tbs ON (ses.id = tbs.sample_event_id)
                LEFT JOIN transect_belt_fish tbfs ON (ses.id = tbfs.sample_event_id)
                LEFT JOIN quadrat_collection qcs ON (ses.id = qcs.sample_event_id)
                LEFT JOIN quadrat_transect qts ON (ses.id = qts.sample_event_id)
                WHERE management.project_id = %(project_id)s
                AND (
                    tbs.id IS NOT NULL OR
                    tbfs.id IS NOT NULL OR
                    qcs.id IS NOT NULL OR
                    qts.id IS NOT NULL
                )
            )
            SELECT management_id AS id
            FROM se_mrs
            WHERE (
                management_id != %(mr_id)s
                AND site_id = %(site_id)s
            )
        """
        params = {
            "site_id": str(site_id),
            "mr_id": str(management_id),
            "project_id": str(project_id),
        }

        return Management.objects.raw(match_sql, params)

    def _duplicate_by_name(self, project_id, management_id, name):
        match_sql = """
            WITH se_mrs AS (
                SELECT DISTINCT management_id, management.name AS management_name FROM
                sample_event ses
                INNER JOIN management ON (ses.management_id = management.id)
                LEFT JOIN transect_benthic tbs ON (ses.id = tbs.sample_event_id)
                LEFT JOIN transect_belt_fish tbfs ON (ses.id = tbfs.sample_event_id)
                LEFT JOIN quadrat_collection qcs ON (ses.id = qcs.sample_event_id)
                LEFT JOIN quadrat_transect qts ON (ses.id = qts.sample_event_id)
                WHERE management.project_id = %(project_id)s
                AND (
                    tbs.id IS NOT NULL OR
                    tbfs.id IS NOT NULL OR
                    qcs.id IS NOT NULL OR
                    qts.id IS NOT NULL
                )
            )
            SELECT management_id AS id
            FROM se_mrs
            WHERE (
                management_id != %(mr_id)s
                AND
                    LOWER(
                        REPLACE(
                            REPLACE(
                                REPLACE(management_name, ' ', ''),
                                '_',
                                ''
                            ),
                            '-',
                            ''
                        )
                    )::text =
                    LOWER(
                        REPLACE(
                            REPLACE(
                                REPLACE(%(name)s, ' ', ''),
                                '_',
                                ''
                            ),
                            '-',
                            ''
                        )
                    )::text
            )
        """
        params = {
            "name": name,
            "mr_id": str(management_id),
            "project_id": str(project_id),
        }
        return Management.objects.raw(match_sql, params)

    @validator_result
    def __call__(self, collect_record, **kwargs):
        management_id = self.get_value(collect_record, self.management_path) or ""
        site_id = self.get_value(collect_record, self.site_path) or ""
        try:
            check_uuid(management_id)
            check_uuid(site_id)
            management = Management.objects.get_or_none(id=management_id)
            site = Site.objects.get_or_none(id=site_id)
        except ParseError:
            management = None
            site = None

        if management is None:
            return ERROR, self.MANAGEMENT_NOT_FOUND

        if site is None:
            return ERROR, self.SITE_NOT_FOUND

        project_id = management.project_id
        name = management.name

        qry = self._duplicate_by_site(project_id, management_id, site_id)
        results = qry[:3]
        if len(results) > 0:
            matches = [str(r.id) for r in results]
            return WARN, self.NOT_UNIQUE, {"matches": matches}

        qry = self._duplicate_by_name(project_id, management_id, name)
        results = qry[:3]
        if len(results) > 0:
            matches = [str(r.id) for r in results]
            return WARN, self.SIMILAR_NAME, {"matches": matches}

        return OK


class ManagementRuleValidator(BaseValidator):
    REQUIRED_RULES = "required_management_rules"

    def __init__(self, management_path, **kwargs):
        self.management_path = management_path
        super().__init__(**kwargs)

    @validator_result
    def __call__(self, collect_record, **kwargs):
        management_id = self.get_value(collect_record, self.management_path) or None

        management = Management.objects.get_or_none(id=management_id)
        if not management or not management.rules:
            return ERROR, self.REQUIRED_RULES

        return OK
