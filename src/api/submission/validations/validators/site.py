from rest_framework.exceptions import ParseError

from ....exceptions import check_uuid
from ....models import Site
from ....utils.duplicates import NOT_UNIQUE_SITE_CODE, find_duplicate_sites
from .base import ERROR, OK, WARN, BaseValidator, validator_result


class UniqueSiteValidator(BaseValidator):
    SITE_NOT_FOUND = "site_not_found"
    NOT_UNIQUE = NOT_UNIQUE_SITE_CODE

    def __init__(self, site_path, **kwargs):
        self.site_path = site_path
        super().__init__(**kwargs)

    @validator_result
    def __call__(self, collect_record, **kwargs):
        # 1. Location within buffer
        # 2. Fuzzy match site name

        site_id = self.get_value(collect_record, self.site_path) or ""
        try:
            check_uuid(site_id)
            site = Site.objects.get_or_none(id=site_id)
        except ParseError:
            site = None

        if site is None:
            return ERROR, self.SITE_NOT_FOUND

        duplicate_sites = find_duplicate_sites(
            project_id=site.project_id, name=site.name, location=site.location, exclude_id=site.id
        )

        if len(duplicate_sites) > 0:
            matches = [str(r.id) for r in duplicate_sites[:3]]
            return WARN, self.NOT_UNIQUE, {"matches": matches}

        return OK
