import datetime

from django.db.models.query import QuerySet
from django.http import HttpResponseBadRequest, StreamingHttpResponse
from django.utils.text import get_valid_filename

from api.models import Project
from api.reports import RawCSVReport


def _get_related_records(qs, report_model_cls, relationship):
    assert report_model_cls is not None
    assert relationship is not None

    view_set_field, model_cls_field = relationship
    pks = qs.values_list(view_set_field, flat=True)

    if isinstance(report_model_cls, QuerySet):
        data_source_query_set = report_model_cls
    else:
        data_source_query_set = report_model_cls.objects.none()

    return data_source_query_set.filter(**{f"{model_cls_field}__in": pks})


def get_serialized_data(
    project_api_viewset,
    serializer_class,
    project_pk,
    report_model_cls=None,
    relationship=None,
    order_by=None,
):
    qs = project_api_viewset.limit_to_project(None, None, project_pk=project_pk)
    qs = project_api_viewset.filter_queryset(qs)

    if report_model_cls or relationship:
        records = _get_related_records(qs, report_model_cls, relationship)
    else:
        records = qs

    return serializer_class(records).get_serialized_data(order_by=order_by)


def _get_csv_response(file_name, fields, data):
    report = RawCSVReport()
    stream = report.stream(fields, data)

    response = StreamingHttpResponse(stream, content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{file_name}"'

    return response


def get_csv_response(
    project_api_viewset,
    serializer_class,
    project_pk,
    report_model_cls=None,
    relationship=None,
    order_by=None,
    file_name_prefix="fieldreport",
):
    project = Project.objects.get_or_none(pk=project_pk)

    if project is None:
        return HttpResponseBadRequest("Project does not exist")

    serialized_data = get_serialized_data(
        project_api_viewset=project_api_viewset,
        serializer_class=serializer_class,
        project_pk=project_pk,
        report_model_cls=report_model_cls,
        relationship=relationship,
        order_by=order_by,
    )

    fields = [f.display for f in serializer_class.get_fields()]

    project_name = get_valid_filename(project.name)[:100]
    time_stamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%d")

    file_name = f"{project_name}-{time_stamp}.csv"
    if file_name_prefix:
        file_name = f"{file_name_prefix}-{file_name}"

    return _get_csv_response(file_name, fields, serialized_data)
