import csv

from rest_framework.exceptions import NotFound

from api import mocks
from api.ingest import (
    BenthicLITCSVSerializer,
    BenthicPhotoQTCSVSerializer,
    BenthicPITCSVSerializer,
    BleachingCSVSerializer,
    FishBeltCSVSerializer,
    HabitatComplexityCSVSerializer, ingest_serializers,
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
        s.name: str(s.id)
        for s in Site.objects.filter(project_id=project_id)
    }

    project_choices["data__sample_event__management"] = {
        m.name: str(m.id)
        for m in Management.objects.filter(project_id=project_id)
    }

    project_choices["data__observers"] = {
        pp.profile.email: ProjectProfileSerializer(instance=pp).data
        for pp in ProjectProfile.objects.select_related("profile").filter(
            project_id=project_id
        )
    }

    return project_choices


def get_ingest_schema(sample_unit, project_pk=None):
    serializer = None
    sample_unit = sample_unit.lower()
    for ingest_serializer in ingest_serializers:
        if ingest_serializer.protocol == sample_unit.lower():
            serializer = ingest_serializer
            break
    if serializer is None:
        raise NotFound(detail=f"{sample_unit} sample unit not found")

    schema = []
    project_choices = None
    if project_pk:
        project_choices = get_ingest_project_choices(project_pk)
    instance = serializer(project_choices=project_choices, many=True)
    choice_sets = instance.get_choices_sets()
    for fieldname, fieldprops in serializer.header_map.items():
        fieldname_simple = "__".join(fieldname.split("__")[1:])

        choices = None
        if fieldname in choice_sets and choice_sets[fieldname]:
            choices = [name for name, id in choice_sets[fieldname].items()]

        field_def = {
            "name": fieldname_simple,
            "label": fieldprops["label"],
            "required": fieldprops["label"].endswith("*"),
            "description": fieldprops["description"],
            "choices": choices,
        }
        schema.append(field_def)

    return schema


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

    schema = [v["label"] for v in serializer.header_map.values()]
    _schema_check(reader.fieldnames, schema)

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
    record_ids = []
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
