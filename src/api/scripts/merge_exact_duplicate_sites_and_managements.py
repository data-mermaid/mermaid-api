"""
The only duplicates that can be merged without a project's say-so are ones where every
content field already matches -- merging changes nothing substantive, so no
judgment call is being made. Only rows with at
least one submitted sample unit are candidates (an idle row can't produce a
duplicate summary sample event), TEST-status projects are excluded, rows are
grouped by (project, name), and a group is "exact" only if every content field
matches across all rows (1m tolerance on site location; management boundary
must match exactly as WKT text, with null boundaries only considered equal to
other nulls; order-independent set comparison for management parties).

Merging itself is delegated entirely to the existing
`api.utils.replace.replace_sampleunit_objs` -- the same function backing
`PUT /projects/<id>/find_and_replace_sites/` and
`.../find_and_replace_managements/` (api/resources/project.py:655-692). No new
merge logic. Within a group, the oldest row (by created_on) is kept and the
rest are merged into it.

One correction is applied on top: `replace_sampleunit_objs` concatenates
`notes` from every merged row with a blank line between them, which is right
when notes differ but corrupts an *exact* group -- since every row in an
exact group has identical notes by definition, concatenating them just
duplicates the same text. So after
the shared merge call, the canonical row's notes are reset to the group's
single agreed-upon value.

Defaults to a dry run that only prints what it would do. Pass "commit" as a
script arg to actually perform the merges.
"""

import math
from collections import defaultdict

from django.db import connection, transaction

from api.models import Management, Site
from api.utils.replace import replace_sampleunit_objs

PROJECT_TEST_STATUS = 80  # Project.TEST -- "real" projects are OPEN(90)/LOCKED(10)

SITE_CONTENT_FIELDS = ["notes", "country_id", "exposure_id", "reef_type_id", "reef_zone_id"]
MGMT_CONTENT_FIELDS = [
    "name_secondary",
    "est_year",
    "notes",
    "size",
    "no_take",
    "periodic_closure",
    "open_access",
    "size_limits",
    "gear_restriction",
    "species_restriction",
    "compliance_id",
    "access_restriction",
]
LOCATION_TOLERANCE_M = 1

_SUBMITTED_SU_EXISTS = """
    EXISTS (SELECT 1 FROM transect_benthic tb WHERE tb.sample_event_id = se.id)
    OR EXISTS (SELECT 1 FROM transect_belt_fish tbf WHERE tbf.sample_event_id = se.id)
    OR EXISTS (SELECT 1 FROM quadrat_collection qc WHERE qc.sample_event_id = se.id)
    OR EXISTS (SELECT 1 FROM quadrat_transect qt WHERE qt.sample_event_id = se.id)
"""


def _dictfetchall(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _fetch_data_bearing_sites(cursor):
    cursor.execute(
        f"""
        SELECT
            s.id, s.project_id, p.name AS project_name, s.name,
            ST_X(s.location) AS lon, ST_Y(s.location) AS lat,
            s.notes, s.country_id, s.exposure_id, s.reef_type_id, s.reef_zone_id,
            s.created_on
        FROM site s
        INNER JOIN project p ON p.id = s.project_id
        WHERE p.status != %(test_status)s
        AND EXISTS (
            SELECT 1 FROM sample_event se
            WHERE se.site_id = s.id AND ({_SUBMITTED_SU_EXISTS})
        )
        """,
        {"test_status": PROJECT_TEST_STATUS},
    )
    return _dictfetchall(cursor)


def _fetch_data_bearing_managements(cursor):
    cursor.execute(
        f"""
        SELECT
            m.id, m.project_id, p.name AS project_name, m.name, m.name_secondary,
            m.est_year, m.notes, ST_AsText(m.boundary::geometry) AS boundary_wkt,
            m.size, m.no_take, m.periodic_closure, m.open_access, m.size_limits,
            m.gear_restriction, m.species_restriction, m.compliance_id,
            m.access_restriction, m.created_on
        FROM management m
        INNER JOIN project p ON p.id = m.project_id
        WHERE p.status != %(test_status)s
        AND EXISTS (
            SELECT 1 FROM sample_event se
            WHERE se.management_id = m.id AND ({_SUBMITTED_SU_EXISTS})
        )
        """,
        {"test_status": PROJECT_TEST_STATUS},
    )
    rows = _dictfetchall(cursor)
    ids = [str(r["id"]) for r in rows]
    parties = defaultdict(set)
    if ids:
        cursor.execute(
            "SELECT management_id, managementparty_id FROM management_parties "
            "WHERE management_id = ANY(%s)",
            [ids],
        )
        for management_id, party_id in cursor.fetchall():
            parties[str(management_id)].add(str(party_id))
    for r in rows:
        r["parties"] = frozenset(parties.get(str(r["id"]), set()))
    return rows


def _group_by_project_and_name(rows):
    groups = defaultdict(list)
    for r in rows:
        groups[(str(r["project_id"]), r["name"])].append(r)
    return [rows for rows in groups.values() if len(rows) > 1]


def _points_close(lon1, lat1, lon2, lat2):
    # rough equirectangular approximation, fine at LOCATION_TOLERANCE_M scale
    r = 6371000
    lat_rad = math.radians((lat1 + lat2) / 2)
    dx = math.radians(lon2 - lon1) * math.cos(lat_rad) * r
    dy = math.radians(lat2 - lat1) * r
    return math.sqrt(dx * dx + dy * dy) <= LOCATION_TOLERANCE_M


def _is_exact_site_group(rows):
    for field in SITE_CONTENT_FIELDS:
        if len({str(r[field]) for r in rows}) > 1:
            return False
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            if not _points_close(rows[i]["lon"], rows[i]["lat"], rows[j]["lon"], rows[j]["lat"]):
                return False
    return True


def _is_exact_management_group(rows):
    for field in MGMT_CONTENT_FIELDS:
        if len({str(r[field]) for r in rows}) > 1:
            return False
    boundary_values = {r["boundary_wkt"] for r in rows}
    if len(boundary_values) > 1:
        non_null = {v for v in boundary_values if v is not None}
        if len(non_null) > 1 or (non_null and None in boundary_values):
            return False
    if len({r["parties"] for r in rows}) > 1:
        return False
    return True


def _merge_group(model_cls, field_name, rows, dry_run):
    rows = sorted(rows, key=lambda r: (r["created_on"], str(r["id"])))
    canonical_id = rows[0]["id"]
    dup_ids = [r["id"] for r in rows[1:]]
    label = (
        f"[{rows[0]['project_name']}] {field_name} {rows[0]['name']!r}: "
        f"keep {canonical_id}, merge {dup_ids}"
    )

    if dry_run:
        print(f"DRY RUN would merge -- {label}")
        return

    with transaction.atomic():
        sid = transaction.savepoint()
        try:
            replace_obj = model_cls.objects.get(id=canonical_id, project_id=rows[0]["project_id"])
            find_objs = model_cls.objects.filter(id__in=dup_ids, project_id=rows[0]["project_id"])
            results = replace_sampleunit_objs(find_objs, replace_obj, field_name, None)

            # Every row in an exact group has identical notes by definition, so
            # replace_sampleunit_objs's differing-notes concatenation just
            # duplicates the same text here. Restore the single agreed value.
            single_notes = rows[0]["notes"] or ""
            replace_obj.refresh_from_db(fields=["notes"])
            if replace_obj.notes != single_notes:
                replace_obj.notes = single_notes
                replace_obj.save()

            transaction.savepoint_commit(sid)
            print(f"MERGED -- {label} -> {results}")
        except Exception as exc:
            transaction.savepoint_rollback(sid)
            print(f"FAILED to merge -- {label}: {exc!r}")


def run(*args):
    dry_run = "commit" not in args

    if dry_run:
        print(
            "DRY RUN mode -- no changes will be made. Pass --script-args commit to merge for real.\n"
        )
    else:
        print("COMMIT mode -- this WILL modify the database.\n")

    with connection.cursor() as cursor:
        site_rows = _fetch_data_bearing_sites(cursor)
        mgmt_rows = _fetch_data_bearing_managements(cursor)

    site_groups = [g for g in _group_by_project_and_name(site_rows) if _is_exact_site_group(g)]
    mgmt_groups = [
        g for g in _group_by_project_and_name(mgmt_rows) if _is_exact_management_group(g)
    ]

    print(
        f"Found {len(site_groups)} exact-duplicate site group(s) and "
        f"{len(mgmt_groups)} exact-duplicate management group(s) to merge.\n"
    )

    for rows in site_groups:
        _merge_group(Site, "site", rows, dry_run)
    for rows in mgmt_groups:
        _merge_group(Management, "management", rows, dry_run)

    print("\nDone.")
