from django.core.cache import cache
from rest_framework.decorators import api_view
from rest_framework.exceptions import (
    ValidationError,
    NotAuthenticated,
    PermissionDenied,
)
from rest_framework.response import Response

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
        "required_filters": PROJECT_FILTERS,
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


class ViewRequest:
    def __init__(self, user, headers, method="GET"):
        self.user = user
        self.data = {}
        self.query_params = {}
        self.GET = {}
        self.META = {}
        self.method = method
        self.headers = headers


def _create_view_request(request, method=None, data=None):
    data = data or {}

    method = method or request.method
    vw_request = ViewRequest(user=request.user, headers=request.headers, method=method)
    for k, v in data.items():
        vw_request.data[k] = v

    vw_request.META = request.META
    vw_request.authenticators = request.authenticators
    vw_request.successful_authenticator = request.successful_authenticator

    return vw_request


def _get_source(source_type):
    return project_sources.get(source_type) or non_project_sources.get(source_type)


def _get_required_parameters(request, data, required_filters):
    params = {"revision_num": data.get("last_revision")}

    if "project" in required_filters:
        project = data.get("project")
        if project is None:
            raise ValueError("Project is missing")
        params["project"] = project

    if "profile" in required_filters:
        user = request.user
        if user is None:
            raise ValueError("Profile is missing")

        params["profile"] = str(user.profile.pk)

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
    return {"status_code": status_code, "message": str(exception), "data": data}


def _format_errors(errors):
    if errors is None:
        return None

    return {k: v[0] for k, v in errors.items()}


def _get_serialized_record(serializer, record_id):
    record = get_record(model_class=serializer.Meta.model, record_id=record_id)

    data = serialize_revisions(serializer, [record])
    if data["updates"]:
        return data["updates"][0]
    elif data["deletes"]:
        return data["deletes"][0]

    return None


def _update_source_record(source_type, serializer, record, request):
    src = _get_source(source_type)
    vw_request = _create_view_request(
        request, method=get_request_method(record), data=record
    )

    record_id = record.get("id")
    failed_permission_checks = check_permissions(
        vw_request, {source_type: record}, [source_type]
    )

    if failed_permission_checks:
        status_code, _ = failed_permission_checks[0]
        exception = NotAuthenticated if status_code == 401 else PermissionError
        return _error(403, exception())

    if record_id is None:
        return _error(
            400, ValidationError(), data={"id": "This field may not be null."}
        )

    if src["read_only"] is True:
        return _error(405, ReadOnlyError(f"{source_type} is read-only"))

    try:
        status_code, errors = apply_changes(vw_request, serializer, record)
        if status_code == 400:
            msg = "Validation Error"
            data = _format_errors(errors)
        elif status_code == 409:
            msg = "Conflict"
            data = _get_serialized_record(serializer, record_id)
        else:
            msg = ""
            data = _get_serialized_record(serializer, record_id)

        return {"status_code": status_code, "message": msg, "data": data}
    except Exception as err:
        print(err)
        return _error(500, err)


def _update_source_records(source_type, records, request):
    src = _get_source(source_type)
    response = []
    if source_type == CHOICES_SOURCE_TYPE:
        # Since choices data structure is different than other
        # source types, it needs to be handled differently.
        return [_error(405, ReadOnlyError(f"{CHOICES_SOURCE_TYPE} area read-only"))]

    serializer = src["view"].serializer_class

    for record in records:
        result = _update_source_record(source_type, serializer, record, request)
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

    revision_num = req_params["revision_num"]

    if revision_num is None and source_type in CACHEABLE_SOURCE_TYPES:
        data = cache.get(source_type)
        if data is None:
            data = get_serialized_records(src["view"], **req_params)
            cache.set(source_type, data)
        return data

    return get_serialized_records(src["view"], **req_params)


def check_permissions(request, data, source_types, method=False):
    failed_permissions = []
    for source_type in source_types:

        # Need exception for project, so check permissions can work
        # for both pull and push views.
        if source_type == PROJECTS_SOURCE_TYPE:
            data[source_type]["project"] = data[source_type]["id"]

        src = _get_source(source_type)
        try:
            params = _get_required_parameters(
                request, data[source_type], src["required_filters"]
            )
        except ValueError:
            failed_permissions.append(
                (
                    403,
                    source_type,
                )
            )
            continue

        view_request = _create_view_request(request, method=method, data=params)

        vw = src["view"]()
        vw.kwargs = {}

        try:
            vw.check_permissions(view_request)
        except NotAuthenticated:
            failed_permissions.append(
                (
                    401,
                    source_type,
                )
            )
        except PermissionDenied:
            failed_permissions.append(
                (
                    403,
                    source_type,
                )
            )

    return failed_permissions


@api_view(http_method_names=["POST"])
def vw_pull(request):
    request_data = request.data or {}
    source_types = request_data.keys()

    invalid_source_types = _validate_source_types(request_data)
    if invalid_source_types:
        invalid_types = ", ".join(invalid_source_types)
        raise ValidationError(f"Invalid source types: {invalid_types}")

    failed_permission_checks = check_permissions(
        request, request_data, source_types, method="GET"
    )
    if failed_permission_checks:
        status_codes = [r[0] for r in failed_permission_checks]
        failed_src_types = ", ".join(r[1] for r in failed_permission_checks)
        exception = NotAuthenticated if 401 in status_codes else PermissionError
        raise exception(f"{str(exception)}: {failed_src_types}")

    response_data = {
        source_type: _get_source_records(source_type, source_data, request)
        for source_type, source_data in request_data.items()
    }

    return Response(response_data)


@api_view(http_method_names=["POST"])
def vw_push(request):
    request_data = request.data or {}

    invalid_source_types = _validate_source_types(request_data)
    if invalid_source_types:
        invalid_types = ", ".join(invalid_source_types)
        raise ValidationError(f"Invalid source types: {invalid_types}")

    response_data = {}
    for source_type, records in request_data.items():
        result = _update_source_records(source_type, records, request)
        response_data[source_type] = result

    return Response(response_data)
