"""
Single definition of what counts as a "duplicate" Site/Management within a
project. Consumed directly by both the create-time hard-reject
(`SiteDuplicateCheckMixin`/`ManagementDuplicateCheckMixin` in
api/resources/mixins.py) and the collect-record-time warning
(`UniqueSiteValidator`/`UniqueManagementValidator` in
api/submission/validations/validators/), so the thresholds and the "has
submitted data" precondition only need to be right in one place. That
precondition: only match against rows with a submitted sample unit -- an idle
row can't produce a duplicate sample event, so it's not a useful signal.

The "has submitted data" check is always derived from get_subclasses(SampleUnit)
rather than a hardcoded table list, so a new protocol's sample unit model
(e.g. Macroinvertebrate's InvertBeltTransect) is picked up automatically by
every consumer instead of needing to be remembered in more than one place.
"""

from django.contrib.gis.measure import Distance
from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import Q

from ..models import Management, SampleUnit, Site
from . import get_subclasses

SITE_NAME_MATCH_PERCENT = 0.5
SITE_BUFFER_M = 100

# Shared with UniqueSiteValidator.NOT_UNIQUE / UniqueManagementValidator.SIMILAR_NAME
# (api/submission/validations/validators/). Defined here, not there: importing those
# validator modules from api/resources/mixins.py would pull in the whole
# submission.validations package, which circles back to api.signals during app startup.
NOT_UNIQUE_SITE_CODE = "not_unique_site"
SIMILAR_NAME_CODE = "similar_name"


def _has_submitted_sample_unit_q(prefix):
    """
    Q object matching rows with at least one submitted sample unit,
    reachable via the reverse-FK lookup path `prefix` to SampleEvent (e.g.
    "sample_events" from Site). Management uses the raw-SQL equivalent,
    submitted_sample_unit_sql, instead.
    """
    q = Q()
    for suclass in get_subclasses(SampleUnit):
        q |= Q(**{f"{prefix}__{suclass._meta.model_name}__isnull": False})
    return q


def submitted_sample_unit_sql():
    """
    Raw-SQL equivalent of _has_submitted_sample_unit_q, for callers building
    a query around a `sample_event ses` alias rather than the ORM (used by
    find_duplicate_managements below and by
    UniqueManagementValidator._duplicate_by_site). Returns (join_sql,
    exists_sql).
    """
    joins = []
    exists_clauses = []
    for suclass in get_subclasses(SampleUnit):
        table = suclass._meta.db_table
        alias = f"su_{table}"
        joins.append(f"LEFT JOIN {table} {alias} ON (ses.id = {alias}.sample_event_id)")
        exists_clauses.append(f"{alias}.id IS NOT NULL")
    return "\n".join(joins), "(" + " OR ".join(exists_clauses) + ")"


def find_duplicate_sites(project_id, name, location, exclude_id):
    """
    Other Sites in `project_id` with a submitted sample unit, within
    SITE_BUFFER_M of `location`, with trigram name similarity to `name` of
    at least SITE_NAME_MATCH_PERCENT.
    """
    if not name or location is None:
        return []

    qry = Site.objects.filter(project_id=project_id).filter(
        _has_submitted_sample_unit_q("sample_events")
    )
    if exclude_id is not None:
        qry = qry.exclude(id=exclude_id)
    qry = (
        qry.filter(location__distance_lt=(location, Distance(m=SITE_BUFFER_M)))
        .annotate(similarity=TrigramSimilarity("name", name))
        .filter(similarity__gte=SITE_NAME_MATCH_PERCENT)
        .order_by("-similarity")
    )

    return list(qry.distinct())


def find_duplicate_managements(project_id, name, exclude_id):
    """
    Other Managements in `project_id`, already used by a SampleEvent with a
    submitted sample unit, whose name normalizes (strip spaces/underscores/
    hyphens, lowercase) to the same value as `name`. Management's other
    duplicate signal, "same site used by a different MR", stays
    validator-only -- see UniqueManagementValidator._duplicate_by_site.
    """
    if not name:
        return []

    join_sql, exists_sql = submitted_sample_unit_sql()
    match_sql = f"""
        WITH se_mrs AS (
            SELECT DISTINCT management_id, management.name AS management_name
            FROM sample_event ses
            INNER JOIN management ON (ses.management_id = management.id)
            {join_sql}
            WHERE management.project_id = %(project_id)s
            AND {exists_sql}
        )
        SELECT management_id AS id
        FROM se_mrs
        WHERE (%(exclude_id)s::uuid IS NULL OR management_id != %(exclude_id)s::uuid)
        AND LOWER(REPLACE(REPLACE(REPLACE(management_name, ' ', ''), '_', ''), '-', ''))::text
          = LOWER(REPLACE(REPLACE(REPLACE(%(name)s, ' ', ''), '_', ''), '-', ''))::text
    """
    params = {
        "name": name,
        "exclude_id": str(exclude_id) if exclude_id is not None else None,
        "project_id": str(project_id),
    }
    return list(Management.objects.raw(match_sql, params))
