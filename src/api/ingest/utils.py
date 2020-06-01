import csv
import json

from django.db import connection, transaction

from api import mocks
from api.ingest import (
    BenthicPITCSVSerializer,
    BleachingCSVSerializer,
    FishBeltCSVSerializer,
)
from api.models import (
    BENTHICLIT_PROTOCOL,
    BENTHICPIT_PROTOCOL,
    BLEACHINGQC_PROTOCOL,
    FISHBELT_PROTOCOL,
    HABITATCOMPLEXITY_PROTOCOL,
    CollectRecord,
    Management,
    Profile,
    ProjectProfile,
    Site,
)
from api.resources.project_profile import ProjectProfileSerializer
from api.utils import tokenutils
from api.submission.utils import submit_collect_records, validate_collect_records
from api.submission.validations import ERROR, WARN


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

        try:
            auth_user = profile.authusers.all()[0]
        except IndexError:
            raise ValueError("AuthUser does not exist.")
        token = tokenutils.create_token(auth_user.user_id)
        request = mocks.MockRequest(token=token)

    return {"request": request}


def _append_required_columns(rows, project_id, profile_id):
    _rows = []
    for row in rows:
        row["project"] = project_id
        row["profile"] = profile_id
        _rows.append(row)
    return _rows


def clear_collect_records(project, protocol):
    sql = """
        DELETE FROM {table_name}
        WHERE 
            project_id='{project}' AND 
            data->>'protocol' = '{protocol}';
        """.format(
        table_name=CollectRecord.objects.model._meta.db_table,
        project=project,
        protocol=protocol,
    )
    with connection.cursor() as cursor:
        cursor.execute(sql)
        return cursor.rowcount


def ingest(
    protocol,
    datafile,
    project_id,
    profile_id,
    request=None,
    dry_run=False,
    clear_existing=False,
    bulk_validation=False,
    bulk_submission=False,
    validation_suppressants=None,
    serializer_class=None,
):

    output = dict()
    if dry_run and bulk_validation:
        raise ValueError("bulk_validation not allowed with dry_run.")
    if dry_run and bulk_submission:
        raise ValueError("bulk_submission not allowed with dry_run.")

    if protocol == BENTHICPIT_PROTOCOL:
        serializer = BenthicPITCSVSerializer
    elif protocol == FISHBELT_PROTOCOL:
        serializer = FishBeltCSVSerializer
    elif protocol == BLEACHINGQC_PROTOCOL:
        serializer = BleachingCSVSerializer
    else:
        return None, None, output

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
        output["errors"] = errors
        return None, output

    with transaction.atomic():
        sid = transaction.savepoint()
        new_records = None
        successful_save = False
        try:
            if clear_existing:
                clear_collect_records(project_id, protocol)
            new_records = s.save()
            successful_save = True
        finally:
            if dry_run is True or successful_save is False:
                transaction.savepoint_rollback(sid)
            else:
                transaction.savepoint_commit(sid)

    profile = None
    is_bulk_invalid = False
    if bulk_validation or bulk_submission:
        profile = Profile.objects.get_or_none(id=profile_id)
        if profile is None:
            raise ValueError("Profile does not exist")

        record_ids = [str(r.pk) for r in new_records]
        validation_output = validate_collect_records(
            profile, record_ids, serializer_class, validation_suppressants
        )
        output["validation"] = validation_output
        statuses = [v.get("status") for v in validation_output.values()]
        if WARN in statuses or ERROR in statuses:
            is_bulk_invalid = True

    if bulk_submission and not is_bulk_invalid:
        submit_output = submit_collect_records(
            profile, record_ids, validation_suppressants
        )
        output["submit"] = submit_output

    return new_records, output
