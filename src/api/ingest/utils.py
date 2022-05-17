import csv

from api import mocks
from api.ingest import (
    BenthicLITCSVSerializer,
    BenthicPhotoQTCSVSerializer,
    BenthicPITCSVSerializer,
    BleachingCSVSerializer,
    FishBeltCSVSerializer,
    HabitatComplexityCSVSerializer,
)
from api.models import (
    BENTHICPQT_PROTOCOL,
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
from api.submission.utils import submit_collect_records, validate_collect_records
from api.submission.validations import ERROR, WARN
from api.utils import tokenutils
from django.db import connection, transaction


class InvalidSchema(Exception):
    def __init__(self, message="Invalid Schema", errors=None):
        super().__init__(message)
        self.errors = errors


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


def _add_extra_fields(rows, project_id, profile_id):
    _rows = []
    for row in rows:
        row["project"] = project_id
        row["profile"] = profile_id
        _rows.append(row)
    return _rows


def _schema_check(csv_headers, serializer_headers):
    missing_required_headers = []
    if csv_headers is None:
        raise InvalidSchema(errors=["CSV headers are null"])

    for h in serializer_headers:
        if "*" in h and h not in csv_headers:
            missing_required_headers.append(h)

    if missing_required_headers:
        print(missing_required_headers)
        raise InvalidSchema(errors=missing_required_headers)


def clear_collect_records(project, profile, protocol):
    sql = """
        DELETE FROM {table_name}
        WHERE 
            project_id='{project}' AND 
            profile_id='{profile}' AND 
            data->>'protocol' = '{protocol}';
        """.format(
        table_name=CollectRecord.objects.model._meta.db_table,
        project=project,
        profile=profile,
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

    if protocol == BENTHICLIT_PROTOCOL:
        serializer = BenthicLITCSVSerializer
    elif protocol == BENTHICPIT_PROTOCOL:
        serializer = BenthicPITCSVSerializer
    elif protocol == FISHBELT_PROTOCOL:
        serializer = FishBeltCSVSerializer
    elif protocol == HABITATCOMPLEXITY_PROTOCOL:
        serializer = HabitatComplexityCSVSerializer
    elif protocol == BLEACHINGQC_PROTOCOL:
        serializer = BleachingCSVSerializer
    elif protocol == BENTHICPQT_PROTOCOL:
        serializer = BenthicPhotoQTCSVSerializer
    else:
        return None, output

    reader = csv.DictReader(datafile)

    _schema_check(reader.fieldnames, list(serializer.header_map.keys()))

    context = _create_context(profile_id, request)
    rows = _add_extra_fields(reader, project_id, profile_id)
    project_choices = get_ingest_project_choices(project_id)
    profile = Profile.objects.get_or_none(id=profile_id)
    if profile is None:
        raise ValueError("Profile does not exist")

    s = serializer(
        data=rows, many=True, project_choices=project_choices, context=context
    )

    is_valid = s.is_valid()
    errors = s.formatted_errors

    if is_valid is False:
        output["errors"] = errors[0:1000]
        return None, output

    with transaction.atomic():
        sid = transaction.savepoint()
        new_records = None
        successful_save = False
        try:
            if clear_existing:
                # Fetch ids to be deleted before deleting
                # because it's being done in a thread and
                # we want to avoid deleting new collect records.
                clear_collect_records(project_id, profile_id, protocol)

            new_records = s.save()
            successful_save = True
        finally:
            if dry_run is True or successful_save is False:
                transaction.savepoint_rollback(sid)
            else:
                transaction.savepoint_commit(sid)

    is_bulk_invalid = False
    if dry_run is False and bulk_validation or bulk_submission:
        record_ids = [str(r.pk) for r in new_records]
        validation_output = validate_collect_records(
            profile, record_ids, serializer_class, validation_suppressants
        )
        output["validate"] = validation_output
        statuses = [v.get("status") for v in validation_output.values()]
        if WARN in statuses or ERROR in statuses:
            is_bulk_invalid = True

    if dry_run is False and bulk_submission and not is_bulk_invalid:
        submit_output = submit_collect_records(
            profile, record_ids, validation_suppressants
        )
        output["submit"] = submit_output

    return new_records, output
