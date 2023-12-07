import uuid

from api.models import AuthUser, Project

SUMMARY_URL_SUFFIXES = (
    "/beltfishes/obstransectbeltfishes/",
    "/beltfishes/sampleunits/",
    "/beltfishes/sampleevents/",
    "/benthiclits/obstransectbenthiclits/",
    "/benthiclits/sampleunits/",
    "/benthiclits/sampleevents/",
    "/benthicpits/obstransectbenthicpits/",
    "/benthicpits/sampleunits/",
    "/benthicpits/sampleevents/",
    "/bleachingqcs/obscoloniesbleacheds/",
    "/bleachingqcs/obsquadratbenthicpercents/",
    "/bleachingqcs/sampleunits/",
    "/bleachingqcs/sampleevents/",
    "/habitatcomplexities/obshabitatcomplexities/",
    "/habitatcomplexities/sampleunits/",
    "/habitatcomplexities/sampleevents/",
    "/benthicpqts/obstransectbenthicpqts/",
    "/benthicpqts/sampleunits/",
    "/benthicpqts/sampleevents/",
    # "/summarysampleevents/",
)
SUBMIT_URL_SUFFIX = "/submit/"
PROJECT_URL_PREFIX = "/v1/projects/"
SUMMARY_EVENT_TYPE = "summary"
PROJECT_EVENT_TYPE = "project"
SUBMIT_EVENT_TYPE = "submit"
OTHER_EVENT_TYPE = "other"
EVENT_TYPES_FILTER = (SUMMARY_EVENT_TYPE, PROJECT_EVENT_TYPE, SUBMIT_EVENT_TYPE)
PROFILE_DEFAULT = {"first_name": "", "last_name": "", "email": ""}
PROJECT_DEFAULT = {"project_name": "", "project_tags": "", "profiles": {}}


def meta(method):
    def _meta(*args, **kw):
        args = list(args)
        log_event = args[0]
        log_event.meta = getattr(log_event, "meta", {})
        args[0] = log_event
        return method(*args, **kw)

    return _meta


@meta
def get_auth_id(log_event):
    user_id = log_event.event.get("user_id")
    auth_type = log_event.event.get("auth_type")
    if user_id is None or auth_type is None:
        return None

    return f"{auth_type}|{user_id}"


@meta
def tag_event_type(log_event):
    path = log_event.event.get("path")
    if path.endswith(SUBMIT_URL_SUFFIX):
        log_event.meta["event_type"] = SUBMIT_EVENT_TYPE
    elif list(filter(path.endswith, SUMMARY_URL_SUFFIXES)) != []:
        log_event.meta["event_type"] = SUMMARY_EVENT_TYPE
    elif path.startswith(PROJECT_URL_PREFIX) and path != PROJECT_URL_PREFIX:
        log_event.meta["event_type"] = PROJECT_EVENT_TYPE
    else:
        log_event.meta["event_type"] = OTHER_EVENT_TYPE
    return log_event


@meta
def tag_project_id(log_event):
    path = log_event.event.get("path").split("/")
    project_id = path[3] if len(path) >= 4 else None
    try:
        uuid.UUID(project_id)
        log_event.meta["project_id"] = project_id
    except (ValueError, TypeError) as _:
        log_event.meta["project_id"] = None

    return log_event


def get_profile_lookup(log_events):
    profile_lookup = {}
    for log_event in log_events:
        auth_id = get_auth_id(log_event)
        if auth_id is None:
            continue
        profile_lookup[auth_id] = None

    return {
        au.user_id: {
            "profile_id": str(au.profile.id),
            "first_name": au.profile.first_name,
            "last_name": au.profile.last_name,
            "email": au.profile.email,
        }
        for au in AuthUser.objects.filter(user_id__in=profile_lookup.keys())
    }


def get_project_lookup(log_events):
    project_lookup = {
        log_event.meta["project_id"]: None
        for log_event in log_events
        if hasattr(log_event, "meta") is not False and log_event.meta.get("project_id") is not None
    }
    return {
        str(p.id): {
            "project_name": p.name,
            "project_status": p.get_status_display(),
            "project_tags": ",".join(t.name for t in p.tags.all()),
            "countries": ",".join(set([s.country.name for s in p.sites.order_by("country__name")])),
            "profiles": {str(pp.profile.id): pp.get_role_display() for pp in p.profiles.all()},
        }
        for p in Project.objects.prefetch_related("profiles", "tags", "sites").filter(
            id__in=project_lookup.keys()
        )
    }


@meta
def create_agg_entry_key(log_event):
    date = str(log_event.timestamp.date())
    auth_id = get_auth_id(log_event)
    return f"{date}::{log_event.meta.get('project_id')}::{auth_id}"


@meta
def create_agg_entry(log_event, profile_lookup, project_lookup):
    auth_id = get_auth_id(log_event)
    profile = profile_lookup.get(auth_id) or PROFILE_DEFAULT
    project = project_lookup.get(log_event.meta.get("project_id")) or PROJECT_DEFAULT
    role = (project.get("profiles") or {}).get(profile.get("profile_id")) or ""

    agg = {
        "date": str(log_event.timestamp.date()),
        "num_submitted": 0,
        "num_summary_views": 0,
        "num_project_calls": 0,
        "role": role,
    }
    agg |= profile
    agg |= project

    return agg


def agg_log_events(log_events=None):
    filtered_log_events = []
    for log_event in log_events:
        status_code = log_event.event.get("status_code") or None
        method = log_event.event.get("method") or ""
        if (
            status_code is None
            or status_code >= 400
            or method.upper() not in ("DELETE", "PUT", "GET", "POST")
        ):
            continue
        log_event = tag_event_type(log_event)
        if log_event.meta["event_type"] not in EVENT_TYPES_FILTER:
            continue
        log_event = tag_project_id(log_event)
        filtered_log_events.append(log_event)

    profile_lookup = get_profile_lookup(filtered_log_events)
    project_lookup = get_project_lookup(filtered_log_events)

    agg = {}
    for log_event in filtered_log_events:
        key = create_agg_entry_key(log_event)
        if key not in agg:
            agg[key] = create_agg_entry(log_event, profile_lookup, project_lookup)

        event_type = log_event.meta.get("event_type")
        if event_type == SUBMIT_EVENT_TYPE:
            agg[key]["num_submitted"] += 1
        elif event_type == PROJECT_EVENT_TYPE:
            agg[key]["num_project_calls"] += 1
        elif event_type == SUMMARY_EVENT_TYPE:
            agg[key]["num_summary_views"] += 1

    return list(agg.values())
