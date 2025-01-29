from django.contrib.gis.geos import Polygon
from django.contrib.gis.measure import Distance
from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import Q
from rest_framework.exceptions import ParseError

from ....exceptions import check_uuid
from ....models import SampleUnit, Site
from ....utils import get_subclasses
from .base import ERROR, OK, WARN, BaseValidator, validator_result


class UniqueSiteValidator(BaseValidator):
    SITE_NOT_FOUND = "site_not_found"
    NOT_UNIQUE = "not_unique_site"

    name_match_percent = 0.5
    site_buffer = 100  # m

    search_bbox_size = (0.5, 0.5)
    srid = 4326

    def __init__(self, site_path, **kwargs):
        self.site_path = site_path
        super().__init__(**kwargs)

    def _search_bounding_box(self, location):
        x = location.x
        y = location.y
        x1 = x - self.search_bbox_size[0] / 2.0
        x2 = x + self.search_bbox_size[0] / 2.0
        y1 = y - self.search_bbox_size[1] / 2.0
        y2 = y + self.search_bbox_size[1] / 2.0

        return Polygon((((x1, y1), (x1, y2), (x2, y2), (x2, y1), (x1, y1))), srid=self.srid)

    def _sample_unit_duplicate_sites(self, sample_unit, site, project_id, location):
        # Ignore self and ensure same project
        qry = sample_unit.objects.select_related("sample_event", "sample_event__site").filter(
            ~Q(sample_event__site=site)
        )
        qry = qry.filter(sample_event__site__project_id=project_id)
        if location is not None:
            qry = qry.filter(
                sample_event__site__location__distance_lt=(
                    location,
                    Distance(m=self.site_buffer),
                )
            )

        # Fuzzy name match
        qry = qry.annotate(similarity=TrigramSimilarity("sample_event__site__name", site.name))
        qry = qry.filter(similarity__gte=self.name_match_percent)

        return [r.sample_event.site for r in qry.order_by("-similarity")]

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

        project_id = site.project_id
        location = site.location

        duplicate_sites = []
        for suclass in get_subclasses(SampleUnit):
            duplicate_sites.extend(
                self._sample_unit_duplicate_sites(suclass, site, project_id, location)
            )

        duplicate_sites = list(set(duplicate_sites))

        if len(duplicate_sites) > 0:
            matches = [str(r.id) for r in duplicate_sites[:3]]
            return WARN, self.NOT_UNIQUE, {"matches": matches}

        return OK
