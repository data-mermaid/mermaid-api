from rest_framework.exceptions import ParseError

from ....exceptions import check_uuid
from ....models import Management, Site
from ....utils.duplicates import (
    SIMILAR_NAME_CODE,
    find_duplicate_managements,
    submitted_sample_unit_sql,
)
from ..statuses import ERROR, OK, WARN
from .base import BaseValidator, validator_result


class UniqueManagementValidator(BaseValidator):
    MANAGEMENT_NOT_FOUND = "management_not_found"
    SITE_NOT_FOUND = "site_not_found"
    NOT_UNIQUE = "not_unique_management"
    SIMILAR_NAME = SIMILAR_NAME_CODE

    def __init__(self, management_path, site_path, **kwargs):
        self.management_path = management_path
        self.site_path = site_path
        super().__init__(**kwargs)

    def _duplicate_by_site(self, project_id, management_id, site_id):
        # Finds MRs that:
        # - are not self and in same project,
        # - AND belong to SEs with the same site (but diff MR) as any SE with
        # associated SUs that uses this MR
        join_sql, exists_sql = submitted_sample_unit_sql()
        match_sql = f"""
            WITH se_mrs AS (
                SELECT DISTINCT management_id, site_id FROM
                sample_event ses
                INNER JOIN management ON (ses.management_id = management.id)
                {join_sql}
                WHERE management.project_id = %(project_id)s
                AND {exists_sql}
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
        return find_duplicate_managements(
            project_id=project_id, name=name, exclude_id=management_id
        )

    @validator_result
    def __call__(self, collect_record, **kwargs):
        management_id = self.get_value(collect_record, self.management_path) or ""
        site_id = self.get_value(collect_record, self.site_path) or ""
        try:
            check_uuid(management_id)
            management = Management.objects.get_or_none(id=management_id)
            if management is None:
                return ERROR, self.MANAGEMENT_NOT_FOUND
        except ParseError:
            return ERROR, self.MANAGEMENT_NOT_FOUND
        try:
            check_uuid(site_id)
            # TODO: Is this needed?
            _ = Site.objects.get_or_none(id=site_id)
        except ParseError:
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
    MANAGEMENT_NOT_FOUND = "management_not_found"
    REQUIRED_RULES = "required_management_rules"

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
        if not management.rules:
            return ERROR, self.REQUIRED_RULES

        return OK
