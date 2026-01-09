from collections import defaultdict

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.db.models.fields.related import OneToOneField
from django.utils import timezone
from django.utils.text import slugify

from ..models import (
    BLEACHINGQC_PROTOCOL,
    PROTOCOL_MAP,
    CollectRecord,
    Management,
    Project,
    ProjectProfile,
    SampleEvent,
    SampleUnit,
    Site,
    TransectMethod,
)
from . import delete_instance_and_related_objects, get_value, is_uuid
from .email import mermaid_email


def _get_sample_unit_method_label(sample_unit_method, sample_unit_name):
    number_label = []
    sample_unit = getattr(sample_unit_method, sample_unit_name)
    if hasattr(sample_unit, "number") and sample_unit.number is not None:
        number_label.append(str(sample_unit.number))
    elif sample_unit_method.protocol == BLEACHINGQC_PROTOCOL:
        number_label.append("1")

    if hasattr(sample_unit, "label") and sample_unit.label.strip():
        number_label.append(sample_unit.label)

    return " ".join(number_label)


def get_sample_unit_field(model):
    return next(
        (
            field.name
            for field in model._meta.get_fields()
            if isinstance(field, OneToOneField) and issubclass(field.related_model, SampleUnit)
        ),
        None,
    )


def _create_submitted_sample_unit_method_summary(model_cls, project):
    DEFAULT_UPDATED_BY = "N/A"
    summary = defaultdict(dict)
    protocol = model_cls.protocol
    sample_unit_name = get_sample_unit_field(model_cls)

    if sample_unit_name is None:
        return summary

    qry_filter = {f"{sample_unit_name}__sample_event__site__project_id": project}
    queryset = model_cls.objects.select_related(
        f"{sample_unit_name}",
        f"{sample_unit_name}__sample_event",
        f"{sample_unit_name}__sample_event__site",
        f"{sample_unit_name}__sample_event__management",
        "updated_by",
    ).prefetch_related("observers")
    queryset = queryset.filter(**qry_filter)

    for record in queryset:
        sample_unit = getattr(record, sample_unit_name)
        sample_event = sample_unit.sample_event
        site = sample_event.site
        management = sample_event.management
        site_id = str(site.pk)
        label = _get_sample_unit_method_label(record, sample_unit_name)
        updated_by = DEFAULT_UPDATED_BY
        if sample_unit.updated_by:
            updated_by = sample_unit.updated_by.full_name
        observers = [o.profile_name for o in record.observers.all()]

        if site_id not in summary:
            summary[site_id] = {"site_name": "", "sample_unit_methods": {protocol: []}}

        summary[site_id]["site_name"] = site.name
        summary[site_id]["sample_unit_methods"][protocol].append(
            {
                "id": f"{record.pk}",
                "sample_date": sample_event.sample_date,
                "label": label,
                "management": {
                    "id": management.id,
                    "name": management.name,
                },
                "updated_by": updated_by,
                "observers": observers,
            }
        )

    for site_id in summary:
        s = sorted(
            summary[site_id]["sample_unit_methods"][protocol],
            key=lambda e: f'{e["label"]}:-:{e["sample_date"]}',
        )
        summary[site_id]["sample_unit_methods"][protocol] = s

    return summary


def create_submitted_summary(project):
    summary = {}
    protocols = []
    sample_unit_methods = TransectMethod.__subclasses__()
    for sample_unit_method in sample_unit_methods:
        sample_unit_method_summary = _create_submitted_sample_unit_method_summary(
            sample_unit_method, project
        )

        if not sample_unit_method_summary:
            continue

        protocols.append(sample_unit_method.protocol)
        for site_id in sample_unit_method_summary:
            if site_id not in summary:
                summary[site_id] = sample_unit_method_summary[site_id]
            else:
                summary[site_id]["sample_unit_methods"].update(
                    sample_unit_method_summary[site_id]["sample_unit_methods"]
                )

    return protocols, summary


def _get_collect_record_label(collect_record):
    number_label = []
    sample_unit = collect_record.sample_unit
    number = sample_unit.get("number")
    if collect_record.protocol == BLEACHINGQC_PROTOCOL and number is None:
        number = 1
    label = sample_unit.get("label") or ""
    if number is not None:
        number_label.append(str(number))

    if label.strip():
        number_label.append(label)

    return " ".join(number_label)


def create_collecting_summary(project):
    DEFAULT_SITE_ID = "__null__"
    DEFAULT_MR_ID = "__null__"
    DEFAULT_OBSERVER_NAME = "unnamed observer"
    summary = {}
    collect_records = CollectRecord.objects.select_related("profile").filter(project=project)

    site_ids = []
    mr_ids = []
    for collect_record in collect_records:
        site_id = get_value(collect_record.data or {}, "sample_event.site", ".")
        if is_uuid(site_id) is False:
            continue
        site_ids.append(site_id)
        mr_id = get_value(collect_record.data or {}, "sample_event.management", ".")
        if is_uuid(mr_id) is False:
            continue
        mr_ids.append(mr_id)

    sites = Site.objects.filter(id__in=set(site_ids))
    site_lookup = {str(s.pk): s.name for s in sites}
    managements = Management.objects.filter(id__in=set(mr_ids))
    mr_lookup = {str(mr.pk): mr.name for mr in managements}

    protocols = {}

    for collect_record in collect_records:
        data = collect_record.data or {}
        protocol = get_value(data, "protocol")

        if protocol not in PROTOCOL_MAP:
            continue

        protocols[protocol] = None

        profile = collect_record.profile
        site_id = get_value(data, "sample_event.site", ".")
        if site_id not in site_lookup:
            site_id = DEFAULT_SITE_ID
        mr_id = get_value(data, "sample_event.management", ".")
        if mr_id not in mr_lookup:
            mr_id = DEFAULT_MR_ID

        profile_id = str(profile.pk)

        if site_id not in summary:
            summary[site_id] = {
                "site_name": site_lookup.get(site_id) or DEFAULT_SITE_ID,
                "sample_unit_methods": {protocol: {"profile_summary": {}}},
            }

        if protocol not in summary[site_id]["sample_unit_methods"]:
            summary[site_id]["sample_unit_methods"][protocol] = {"profile_summary": {}}

        if profile_id not in summary[site_id]["sample_unit_methods"][protocol]["profile_summary"]:
            summary[site_id]["sample_unit_methods"][protocol]["profile_summary"][profile_id] = {
                "profile_name": profile.full_name,
                "collect_records": [],
            }

        label = _get_collect_record_label(collect_record)
        sample_date = get_value(data, "sample_event__sample_date")
        mr = mr_lookup.get(mr_id) or DEFAULT_MR_ID
        observers = get_value(data, "observers") or []
        observer_names = [o.get("profile_name") or DEFAULT_OBSERVER_NAME for o in observers]

        summary[site_id]["sample_unit_methods"][protocol]["profile_summary"][profile_id][
            "collect_records"
        ].append(
            {
                "name": label,
                "sample_date": sample_date,
                "management_name": mr,
                "observers": observer_names,
            }
        )

    return list(protocols), summary


@transaction.atomic()
def copy_project_and_resources(owner_profile, new_project_name, original_project):
    new_project = Project.objects.get(id=original_project.pk)
    new_project.id = None
    new_project.name = new_project_name
    new_project.created_by = owner_profile
    new_project.updated_by = owner_profile
    if str(original_project.pk) == str(settings.DEMO_PROJECT_ID):
        new_project.is_demo = True
    new_project.save()

    new_project.tags.add(*original_project.tags.all())

    ProjectProfile.objects.create(
        role=ProjectProfile.ADMIN, project=new_project, profile=owner_profile
    )

    project_profiles = []
    for pp in original_project.profiles.filter(~Q(profile=owner_profile)):
        pp.id = None
        pp.project = new_project
        project_profiles.append(pp)
    ProjectProfile.objects.bulk_create(project_profiles)

    new_sites = []
    for site in original_project.sites.all():
        site.id = None
        site.project = new_project
        new_sites.append(site)
    Site.objects.bulk_create(new_sites)

    new_management_regimes = []
    for mr in original_project.management_set.all():
        mr.id = None
        mr.project = new_project
        new_management_regimes.append(mr)
    Management.objects.bulk_create(new_management_regimes)

    return new_project


def email_members_of_new_project(project, owner_profile):
    for project_profile in project.profiles.filter(~Q(profile=owner_profile)):
        context = {
            "owner": owner_profile,
            "project": project,
            "project_profile": project_profile,
        }
        mermaid_email(
            subject="New Project",
            template="emails/added_to_project.txt",
            to=[project_profile.profile.email],
            context=context,
        )


def get_safe_project_name(project_id):
    try:
        project = Project.objects.get(id=project_id)
        return slugify(project.name, allow_unicode=True).replace("-", "_")
    except Project.DoesNotExist as e:
        raise ValueError(f"Project with id '{project_id}' does not exist") from e


def get_profiles(project):
    return project.profiles.order_by("profile__last_name", "profile__first_name")


def citation_retrieved_text(project_name):
    date_text = timezone.localdate().strftime("%B %-d, %Y")
    domain = settings.DEFAULT_DOMAIN_DASHBOARD
    return f"Retrieved {date_text} from {domain}?project={project_name}."


def default_citation(project, profiles=None):
    if profiles is None:
        profiles = get_profiles(project)
    admin_names = [
        p.profile.citation_name
        for p in profiles
        if p.is_admin is True and p.profile.citation_name is not None
    ]
    year = ""
    latest_se = SampleEvent.objects.filter(site__project=project).order_by("-sample_date").first()
    if latest_se and latest_se.sample_date:
        year = f"{latest_se.sample_date.year}. "
    return f"{', '.join(admin_names)}. {year}{project.name}. MERMAID."


def suggested_citation(project, profiles=None):
    if project is None:
        raise ValueError("Project cannot be None")
    if project.user_citation and project.user_citation.strip():
        return project.user_citation.strip()
    return default_citation(project, profiles)


def delete_project(pk):
    try:
        instance = Project.objects.get(id=pk)
    except Project.DoesNotExist:
        print(f"project {pk} does not exist")
        return

    with transaction.atomic():
        sid = transaction.savepoint()
        try:
            delete_instance_and_related_objects(instance)
            transaction.savepoint_commit(sid)
            print("project deleted")
        except Exception as err:
            print(f"Delete Project: {err}")
            transaction.savepoint_rollback(sid)
