import csv
import json

from api import mocks
from api.ingest import BenthicPITCSVSerializer, FishBeltCSVSerializer
from api.models import Management, ProjectProfile, Site, Profile
from api.resources.project_profile import ProjectProfileSerializer
from api.utils import tokenutils
from django.db import transaction


def get_ingest_project_choices(project_id):
    project_choices = dict()
    project_choices["data__sample_event__site"] = {
        s.name.lower().replace("\t", " "): str(s.id)
        for s in Site.objects.filter(project_id=project_id)
    }

    project_choices["data__sample_event__management"] = {
        m.name.lower().replace("\t", " "): str(m.id)
        for m in Management.objects.filter(project_id=project_id)
    }

    project_choices["project_profiles"] = {
        pp.profile.email.lower(): ProjectProfileSerializer(instance=pp).data
        for pp in ProjectProfile.objects.select_related("profile").filter(
            project_id=project_id
        )
    }

    return project_choices


def _create_context(profile_id, request=None):
    if request is None:
        profile = Profile.objects.get_or_none(id=profile_id)
        if profile is None:
            raise ValueError("[{}] Profile does not exist.".format(profile_id))
        token = tokenutils.create_token("google-oauth2|109519544860798433542")
        request = mocks.MockRequest(token=token)

    return {"request": request}


def _append_required_columns(rows, project_id, profile_id):
    _rows = []
    for row in rows:
        row["project"] = project_id
        row["profile"] = profile_id
        _rows.append(row)
    return _rows


def _ingest(serializer, datafile, project_id, profile_id, request=None, dry_run=False):
    reader = csv.DictReader(datafile)
    context = _create_context(request, profile_id)
    rows = _append_required_columns(reader, project_id, profile_id)
    project_choices = get_ingest_project_choices(project_id)

    s = serializer(
        data=rows, many=True, project_choices=project_choices, context=context
    )

    is_valid = s.is_valid()
    errors = s.formatted_errors

    if is_valid is False:
        return None, [json.dumps(e) for e in errors]

    with transaction.atomic():
        sid = transaction.savepoint()
        new_records = None
        successful_save = False
        try:
            new_records = s.save()
            successful_save = True
        finally:
            if dry_run is True or successful_save is False:
                transaction.savepoint_rollback(sid)
            else:
                transaction.savepoint_commit(sid)

    return new_records, None


def ingest_fishbelt(datafile, project_id, profile_id, request=None, dry_run=False):
    return _ingest(
        FishBeltCSVSerializer,
        datafile,
        project_id,
        profile_id,
        request=request,
        dry_run=dry_run,
    )


def ingest_benthicpit(datafile, project_id, profile_id, request=None, dry_run=False):
    return _ingest(
        BenthicPITCSVSerializer,
        datafile,
        project_id,
        profile_id,
        request=request,
        dry_run=dry_run,
    )
