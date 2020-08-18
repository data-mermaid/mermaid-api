from datetime import datetime

from django.db.models.query import QuerySet
from django.http import HttpResponseBadRequest, StreamingHttpResponse
from django.utils.text import get_valid_filename

from api.models import Project
from api.reports import RawCSVReport


def get_serialized_data(queryset, serializer_class):
    return serializer_class(queryset).get_serialized_data()


def _get_csv_response(file_name, fields, data):
    report = RawCSVReport()
    stream = report.stream(fields, data)

    response = StreamingHttpResponse(stream, content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{file_name}"'

    return response


def get_csv_response(queryset, serializer_class, file_name_prefix="fieldreport"):
    serialized_data = (
        get_serialized_data(queryset=queryset, serializer_class=serializer_class) or []
    )

    fields = [f.display for f in serializer_class.get_fields()]
    # project_name = get_valid_filename(project.name)[:100]
    time_stamp = datetime.utcnow().strftime("%Y%m%d")
    file_name = f"{file_name_prefix}-{time_stamp}.csv"

    return _get_csv_response(file_name, fields, serialized_data)
