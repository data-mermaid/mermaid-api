from collections import defaultdict

from django.db import transaction
from django.db.models import Q
from django.db.models.fields.related import OneToOneField

from ..models import PROTOCOL_MAP, CollectRecord, Project, ProjectProfile, SampleUnit, Site, TransectMethod
from . import get_value, is_uuid
from .email import mermaid_email


def _get_sample_unit_method_label(sample_unit):
    number_label = []
    if hasattr(sample_unit, "number") and sample_unit.number is not None:
        number_label.append(str(sample_unit.number))

    if hasattr(sample_unit, "label") and sample_unit.label.strip():
        number_label.append(sample_unit.label)

    return " ".join(number_label)


def _get_sample_unit_field(model):
    return next(
        (
            field.name
            for field in model._meta.get_fields()
            if isinstance(field, OneToOneField)
            and issubclass(field.related_model, SampleUnit)
        ),
        None,
    )


def _create_submitted_sample_unit_method_summary(model_cls, project):
    summary = defaultdict(dict)
    protocol = model_cls.protocol
    sample_unit_name = _get_sample_unit_field(model_cls)

    if sample_unit_name is None:
        return summary

    qry_filter = {f"{sample_unit_name}__sample_event__site__project_id": project}
    queryset = model_cls.objects.select_related(
        f"{sample_unit_name}",
        f"{sample_unit_name}__sample_event",
        f"{sample_unit_name}__sample_event__site",
    )
    queryset = queryset.filter(**qry_filter)

    for record in queryset:
        sample_unit = getattr(record, sample_unit_name)
        sample_event = sample_unit.sample_event
        site = sample_event.site
        site_id = str(site.pk)
        label = _get_sample_unit_method_label(sample_unit)

        if site_id not in summary:
            summary[site_id] = {"site_name": "", "sample_unit_methods": {protocol: []}}

        summary[site_id]["site_name"] = site.name
        summary[site_id]["sample_unit_methods"][protocol].append(
            {
                "id": f"{record.pk}",
                "sample_date": sample_event.sample_date,
                "label": label,
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
    label = sample_unit.get("label") or ""
    if number is not None:
        number_label.append(str(number))

    if label.strip():
        number_label.append(label)

    return " ".join(number_label)


def create_collecting_summary(project):
    DEFAULT_SITE_ID = "__null__"
    summary = {}
    collect_records = CollectRecord.objects.select_related("profile").filter(
        project=project
    )
    site_ids = []
    for collect_record in collect_records:
        val = get_value(collect_record.data or {}, "sample_event.site", ".")
        if is_uuid(val) is False:
            continue
        site_ids.append(val)

    sites = Site.objects.filter(id__in=set(site_ids))
    site_lookup = {str(s.pk): s.name for s in sites}

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

        profile_id = str(profile.pk)

        if site_id not in summary:
            summary[site_id] = {
                "site_name": site_lookup.get(site_id) or DEFAULT_SITE_ID,
                "sample_unit_methods": {protocol: {"profile_summary": {}}},
            }

        if protocol not in summary[site_id]["sample_unit_methods"]:
            summary[site_id]["sample_unit_methods"][protocol] = {"profile_summary": {}}

        if (
            profile_id
            not in summary[site_id]["sample_unit_methods"][protocol]["profile_summary"]
        ):
            summary[site_id]["sample_unit_methods"][protocol]["profile_summary"][
                profile_id
            ] = {"profile_name": profile.full_name, "labels": []}

        label = _get_collect_record_label(collect_record)
        summary[site_id]["sample_unit_methods"][protocol]["profile_summary"][
            profile_id
        ]["labels"].append(label)

    return list(protocols), summary


def copy_project_and_resources(owner_profile, new_project_name, original_project):
    with transaction.atomic():
        new_project = Project.objects.get(id=original_project.pk)
        new_project.id = None
        new_project.name = new_project_name
        new_project.save()

        new_project.tags.add(*original_project.tags.all())

        ProjectProfile.objects.create(
            role=ProjectProfile.ADMIN,
            project=new_project,
            profile=owner_profile
        )

        for pp in original_project.profiles.filter(~Q(profile=owner_profile)):
            pp.id = None
            pp.project = new_project
            pp.save()
    
        for site in original_project.sites.all():
            site.id = None
            site.project = new_project
            site.save()
        
        for mr in original_project.management_set.all():
            mr.id = None
            mr.project = new_project
            mr.save()

        return new_project


def email_members_of_new_project(project, owner_profile):
    for project_profile in project.profiles.all():
        context = {
            "owner": owner_profile,
            "project": project,
            "project_profile": project_profile
        }
        mermaid_email(
            subject="New Project",
            template="emails/added_to_project.txt",
            to=[project_profile.profile.email],
            context=context
        )
