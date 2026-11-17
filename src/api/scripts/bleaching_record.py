"""
Load an unsubmitted Benthic PIT collect record that includes bleaching statuses.
Each coral point gets a random bleaching status, and the sample date is a random
day in the past.

    ./manage.py runscript bleaching_record
    ./manage.py runscript bleaching_record --script-args project="Project 1" profile=me@example.com
    ./manage.py runscript bleaching_record --script-args date=2026-06-01

Optional script args (key=value):
    project  Project id or name. Default: first open project that has a site,
             a management regime and a collector.
    profile  Email of the collect record owner; must be a collector or admin of
             the project. Default: the project's first admin, else first collector.
    date     Sample date (YYYY-MM-DD), before today. Default: a random day in the
             last MAX_DAYS_AGO days. Reuse a date to put records in one sample event.
"""

import datetime
import random
import uuid
from collections import Counter

from django.utils import timezone

from api.models import (
    BENTHICPIT_PROTOCOL,
    BLEACHING_CATEGORY_HARD_CORAL,
    BLEACHING_CATEGORY_SOFT_CORAL,
    BLEACHING_STATUS_CHOICES,
    BenthicAttribute,
    CollectRecord,
    Management,
    Project,
    ProjectProfile,
    Site,
)

INTERVAL_SIZE = 0.5
INTERVAL_START = 0.5

HARD = "hard"
SOFT = "soft"
OTHER = "other"

# Sample dates are picked from 1 to MAX_DAYS_AGO days before today
MAX_DAYS_AGO = 730

# Attribute kind per point along the transect, in order. Coral points get a random
# bleaching status; non-coral points never take one.
POINTS = [HARD] * 9 + [OTHER] * 2 + [SOFT] * 4 + [OTHER] * 3 + [HARD] + [OTHER]


def _parse_args(args):
    options = {}
    for arg in args:
        key, sep, value = arg.partition("=")
        if not sep or key not in ("project", "profile", "date"):
            raise ValueError(
                f"Unknown argument '{arg}'. "
                "Use project=<id or name> profile=<email> date=<YYYY-MM-DD>"
            )
        options[key] = value
    return options


def _get_sample_date(date_arg, today):
    if not date_arg:
        return today - datetime.timedelta(days=random.randint(1, MAX_DAYS_AGO))

    sample_date = datetime.date.fromisoformat(date_arg)
    if sample_date >= today:
        raise ValueError(f"date must be before today ({today})")
    return sample_date


def _is_uuid(value):
    try:
        uuid.UUID(str(value))
        return True
    except ValueError:
        return False


def _get_project(project_arg):
    if project_arg:
        lookup = {"pk": project_arg} if _is_uuid(project_arg) else {"name": project_arg}
        return Project.objects.get(**lookup)

    collector_projects = ProjectProfile.objects.filter(role__gte=ProjectProfile.COLLECTOR).values(
        "project_id"
    )
    project = (
        Project.objects.filter(
            status__gt=Project.LOCKED,
            pk__in=collector_projects,
        )
        .filter(pk__in=Site.objects.values("project_id"))
        .filter(pk__in=Management.objects.values("project_id"))
        .order_by("name")
        .first()
    )
    if project is None:
        raise ValueError("No open project with a site, a management regime and a collector found")
    return project


def _get_profile(project, email):
    project_profiles = ProjectProfile.objects.select_related("profile").filter(
        project=project, role__gte=ProjectProfile.COLLECTOR
    )
    if email:
        project_profiles = project_profiles.filter(profile__email__iexact=email)

    project_profile = project_profiles.order_by("-role", "created_on").first()
    if project_profile is None:
        who = email or "any profile"
        raise ValueError(f"{who} is not a collector or admin of project '{project.name}'")
    return project_profile.profile


def _get_attributes():
    top_level = BenthicAttribute.objects.filter(parent__isnull=True)
    hard = top_level.get(name=BLEACHING_CATEGORY_HARD_CORAL)
    soft = top_level.get(name=BLEACHING_CATEGORY_SOFT_CORAL)
    other = top_level.exclude(pk__in=[hard.pk, soft.pk]).order_by("name").first()
    if other is None:
        raise ValueError("No non-coral top-level benthic attribute found")
    return {HARD: hard, SOFT: soft, OTHER: other}


def _first_or_error(queryset, label, project):
    obj = queryset.order_by("name").first()
    if obj is None:
        raise ValueError(f"Project '{project.name}' has no {label}")
    return obj


def run(*args):
    options = _parse_args(args)
    project = _get_project(options.get("project"))
    profile = _get_profile(project, options.get("profile"))
    site = _first_or_error(Site.objects.filter(project=project), "site", project)
    management = _first_or_error(
        Management.objects.filter(project=project), "management regime", project
    )
    attributes = _get_attributes()

    now = timezone.now()
    sample_date = _get_sample_date(options.get("date"), timezone.localdate())
    statuses = [val for val, _ in BLEACHING_STATUS_CHOICES]

    observations = []
    status_counts = {HARD: Counter(), SOFT: Counter()}
    for n, kind in enumerate(POINTS):
        status = random.choice(statuses) if kind in status_counts else None
        observation = {
            "id": str(uuid.uuid4()),
            "attribute": str(attributes[kind].pk),
            "interval": INTERVAL_START + n * INTERVAL_SIZE,
        }
        if status is not None:
            observation["bleaching_status"] = status
            status_counts[kind][status] += 1
        observations.append(observation)

    data = {
        "protocol": BENTHICPIT_PROTOCOL,
        "include_bleaching": True,
        "sample_event": {
            "site": str(site.pk),
            "management": str(management.pk),
            "sample_date": f"{sample_date:%Y-%m-%d}",
        },
        "benthic_transect": {
            "number": 1,
            # Keeps reruns from tripping the duplicate transect validation
            "label": f"bleaching {now:%Y%m%d-%H%M%S}",
            "depth": 5,
            "len_surveyed": len(POINTS) * INTERVAL_SIZE,
            "sample_time": "10:00",
        },
        "interval_size": INTERVAL_SIZE,
        "interval_start": INTERVAL_START,
        "obs_benthic_pits": observations,
        "observers": [{"profile": str(profile.pk)}],
    }

    collect_record = CollectRecord.objects.create(
        project=project,
        profile=profile,
        stage=CollectRecord.SAVED_STAGE,
        data=data,
    )

    print(f"Created Benthic PIT collect record {collect_record.pk}")
    print(f"  project:    {project.name} ({project.pk})")
    print(f"  owner:      {profile.email}")
    print(f"  site:       {site.name}")
    print(f"  management: {management.name}")
    print(f"  date:       {sample_date}")
    print(f"  points:     {len(observations)}")
    for kind, counts in status_counts.items():
        total = sum(counts.values())
        summary = ", ".join(
            f"{name} {counts[val]} ({100 * counts[val] / total:.0f}%)"
            for val, name in BLEACHING_STATUS_CHOICES
        )
        print(f"  {kind} coral ({total}): {summary}")
