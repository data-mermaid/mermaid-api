from rest_framework.decorators import api_view
from rest_framework.exceptions import (
    NotAuthenticated,
    NotFound,
    PermissionDenied,
    ValidationError,
)
from rest_framework.response import Response

from api.models import Project
from api.resources import (
    benthic_attribute,
    choices,
    collect_record,
    fish_family,
    fish_genus,
    fish_species,
    pmanagement,
    project,
    project_profile,
    psite,
)
from api import utils
from .utils import create_view_request
from .pull import get_serialized_records, serialize_revisions, get_record
from .push import get_request_method, apply_changes


NO_FILTERS = ()
PROJECT_FILTERS = ("project",)
PROJECT_PROFILE_FILTERS = ("project", "profile")

COLLECT_RECORDS_SOURCE_TYPE = "collect_records"
PROJECT_SITES_SOURCE_TYPE = "project_sites"
PROJECT_MANAGEMENTS_SOURCE_TYPE = "project_managements"
PROJECT_PROFILES_SOURCE_TYPE = "project_profiles"
PROJECTS_SOURCE_TYPE = "projects"
BENTHIC_ATTRIBUTES_SOURCE_TYPE = "benthic_attributes"
FISH_FAMILIES_SOURCE_TYPE = "fish_families"
FISH_GENERA_SOURCE_TYPE = "fish_genera"
FISH_SPECIES_SOURCE_TYPE = "fish_species"
CHOICES_SOURCE_TYPE = "choices"

CACHEABLE_SOURCE_TYPES = (
    BENTHIC_ATTRIBUTES_SOURCE_TYPE,
    FISH_FAMILIES_SOURCE_TYPE,
    FISH_GENERA_SOURCE_TYPE,
    FISH_SPECIES_SOURCE_TYPE,
)


class ReadOnlyError(Exception):
    pass


project_sources = {
    COLLECT_RECORDS_SOURCE_TYPE: {
        "view": collect_record.CollectRecordViewSet,
        "required_filters": PROJECT_PROFILE_FILTERS,
        "read_only": False,
    },
    PROJECT_SITES_SOURCE_TYPE: {
        "view": psite.PSiteViewSet,
        "required_filters": PROJECT_FILTERS,
        "read_only": False,
    },
    PROJECT_MANAGEMENTS_SOURCE_TYPE: {
        "view": pmanagement.PManagementViewSet,
        "required_filters": PROJECT_FILTERS,
        "read_only": False,
    },
    PROJECT_PROFILES_SOURCE_TYPE: {
        "view": project_profile.ProjectProfileViewSet,
        "required_filters": PROJECT_FILTERS,
        "read_only": False,
    },
    PROJECTS_SOURCE_TYPE: {
        "view": project.ProjectViewSet,
        "required_filters": NO_FILTERS,
        "read_only": False,
    },
}

non_project_sources = {
    BENTHIC_ATTRIBUTES_SOURCE_TYPE: {
        "view": benthic_attribute.BenthicAttributeViewSet,
        "required_filters": NO_FILTERS,
        "read_only": False,
    },
    FISH_FAMILIES_SOURCE_TYPE: {
        "view": fish_family.FishFamilyViewSet,
        "required_filters": NO_FILTERS,
        "read_only": True,
    },
    FISH_GENERA_SOURCE_TYPE: {
        "view": fish_genus.FishGenusViewSet,
        "required_filters": NO_FILTERS,
        "read_only": True,
    },
    FISH_SPECIES_SOURCE_TYPE: {
        "view": fish_species.FishSpeciesViewSet,
        "required_filters": NO_FILTERS,
        "read_only": False,
    },
    CHOICES_SOURCE_TYPE: {
        "view": choices.ChoiceViewSet,
        "required_filters": NO_FILTERS,
        "read_only": True,
    },
}


def _get_source(source_type):
    return project_sources.get(source_type) or non_project_sources.get(source_type)


def _get_project(data, source_type):
    projid = None
    projname = "NO PROJECT"
    if "project" in data[source_type]:
        projid = data[source_type].get("project")
    elif source_type == PROJECTS_SOURCE_TYPE and "id" in data[source_type]:
        projid = data[source_type].get("id")

    if projid:
        try:
            if utils.is_uuid(projid) is True:
                proj = Project.objects.get(pk=projid)
                projname = proj.name
        except Project.DoesNotExist:
            pass

    return {"project_id": projid, "project_name": projname}


def _get_profile_id(request):
    user = request.user
    return None if user is None else str(user.profile.pk)


def _get_required_parameters(request, data, required_filters):
    params = {"revision_num": data.get("last_revision")}

    if "project" in required_filters:
        project = data.get("project")
        if project is None:
            raise ValueError("Project is missing")
        params["project"] = project

    if "profile" in required_filters:
        profile_id = _get_profile_id(request)
        if profile_id is None:
            raise ValueError("Profile is missing")

        params["profile"] = profile_id

    return params


def _validate_source_types(data):
    return [st for st in data if _get_source(st) is None]


def _get_choices():
    src = _get_source(CHOICES_SOURCE_TYPE)
    return {
        "updates": src["view"]().get_choices(),
        "deletes": [],
        "last_revision_num": -1,
    }


def _error(status_code, exception, data=None):
    message = str(exception)
    if status_code == 500:
        data = {"name": message}
        message = "Server error"
    return {"status_code": status_code, "message": message, "data": data}


def _format_errors(errors):
    if errors is None:
        return None

    return {k: v[0] for k, v in errors.items()}


def _get_serialized_record(viewset, profile_id, record_id):
    serializer = viewset.serializer_class
    record = get_record(viewset, profile_id, record_id)

    if isinstance(record, dict):
        data = serialize_revisions(serializer, [], [record], [])
    else:
        data = serialize_revisions(serializer, [record], [], [])
    
    if data["updates"]:
        return data["updates"][0]
    elif data["deletes"]:
        return data["deletes"][0]

    return None


def _update_source_record(source_type, serializer, record, request, force=False):
    src = _get_source(source_type)
    vw_request = create_view_request(
        request, method=get_request_method(record), data=record
    )
    viewset = src["view"](request=vw_request)

    record_id = record.get("id")
    permission_checks = check_permissions(
        vw_request, {source_type: record}, [source_type]
    )

    code = permission_checks[source_type]["code"]
    data = permission_checks[source_type]["data"]
    if code in [401, 403]:
        exception = NotAuthenticated if code == 401 else PermissionDenied
        return _error(code, exception(), data)

    if record_id is None:
        return _error(
            400, ValidationError(), data={"id": "This field may not be null."}
        )

    if src["read_only"] is True:
        return _error(405, ReadOnlyError(f"{source_type} is read-only"))

    try:
        profile_id = _get_profile_id(request)
        status_code, msg, errors = apply_changes(vw_request, serializer, record, force=force)
        if status_code == 400:
            data = _format_errors(errors)
        elif status_code == 409:
            data = _get_serialized_record(viewset, profile_id, record_id)
        elif status_code == 418:  # other custom error output
            status_code = 409
            data = errors
        else:
            data = _get_serialized_record(viewset, profile_id, record_id)

        return {"status_code": status_code, "message": msg, "data": data}
    except Exception as err:
        print(err)
        return _error(500, err)


def _update_source_records(source_type, records, request, force=False):
    src = _get_source(source_type)
    response = []
    if source_type == CHOICES_SOURCE_TYPE:
        # Since choices data structure is different than other
        # source types, it needs to be handled differently.
        return [_error(405, ReadOnlyError(f"{CHOICES_SOURCE_TYPE} area read-only"))]

    serializer = src["view"].serializer_class

    for record in records:
        result = _update_source_record(source_type, serializer, record, request, force=force)
        response.append(result)

    return response


def _get_source_records(source_type, source_data, request):
    if source_type == CHOICES_SOURCE_TYPE:
        return _get_choices()

    src = _get_source(source_type)

    try:
        req_params = _get_required_parameters(
            request, source_data, src["required_filters"]
        )
    except ValueError as ve:
        raise ValidationError(str(ve))

    viewset = src["view"](request=request)
    profile_id = _get_profile_id(request)
    return get_serialized_records(viewset, profile_id, required_params=req_params)


def check_permissions(request, data, source_types, method=False):
    permission_checks = {}
    for source_type in source_types:
        src = _get_source(source_type)
        proj = _get_project(data, source_type)
        try:
            params = _get_required_parameters(
                request, data[source_type], src["required_filters"]
            )
        except ValueError:
            permission_checks[source_type] = {
                "data": proj,
                "code": 403
            }
            continue

        view_request = create_view_request(request, method=method, data=params)

        vw = src["view"]()
        vw.kwargs = {}
        if source_type == PROJECTS_SOURCE_TYPE:
            vw.kwargs["pk"] = proj.get("project_id")

        permission_check = {
            "data": proj,
            "code": 200
        }
        try:
            vw.check_permissions(view_request)
        except NotAuthenticated:
            permission_check["code"] = 401
        except PermissionDenied:
            permission_check["code"] = 403
        except NotFound as e:
            print(e)

        permission_checks[source_type] = permission_check

    return permission_checks


@api_view(http_method_names=["POST"])
def vw_pull(request):
    request_data = request.data or {}
    source_types = request_data.keys()

    invalid_source_types = _validate_source_types(request_data)
    if invalid_source_types:
        invalid_types = ", ".join(invalid_source_types)
        raise ValidationError(f"Invalid source types: {invalid_types}")

    permission_checks = check_permissions(
        request, request_data, source_types, method="GET"
    )

    response_data = {}
    for source_type, source_data in request_data.items():
        code = permission_checks[source_type]["code"]
        if code == 200:
            response_data[source_type] = _get_source_records(source_type, source_data, request)
        elif code in [401, 403]:
            source_data["last_revision"] = None
            response = _get_source_records(source_type, source_data, request)
            record_ids = [rec["id"] for rec in response["updates"]]
            record_ids.extend(rec["id"] for rec in response["deletes"])
            response["updates"] = []
            response["deletes"] = []
            response["error"] = {
                "code": code,
                "record_ids": record_ids
            }
            response_data[source_type] = response

    return Response(response_data)


@api_view(http_method_names=["POST"])
def vw_push(request):
    request_data = request.data or {}
    force = utils.truthy(str(request.query_params.get("force")).strip())

    invalid_source_types = _validate_source_types(request_data)
    if invalid_source_types:
        invalid_types = ", ".join(invalid_source_types)
        raise ValidationError(f"Invalid source types: {invalid_types}")

    response_data = {}
    source_types = list(request_data.keys())
    if PROJECTS_SOURCE_TYPE in source_types:
        source_types.remove(PROJECTS_SOURCE_TYPE)
        source_types.insert(0, PROJECTS_SOURCE_TYPE)

    for source_type in source_types:
        records = request_data[source_type]
        result = _update_source_records(source_type, records, request, force=force)
        response_data[source_type] = result

    return Response(response_data)
