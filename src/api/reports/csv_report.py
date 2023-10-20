from datetime import datetime

from django.db.models.query import QuerySet
from django.http import HttpResponseBadRequest, StreamingHttpResponse
from django.utils.text import get_valid_filename

from api.models import Project
from api.reports import RawCSVReport
from api.reports.report_serializer import ReportSerializer


def get_fields(serializer_class, include_additional_fields, show_display_fields):
    serializer = serializer_class(
        include_additional_fields=include_additional_fields,
        show_display_fields=show_display_fields,
    )
    if show_display_fields is True:
        return [f.display for f in serializer.get_fields()]
    else:
        return [f.alias or f.column_path for f in serializer.get_fields()]


def get_data(
    serializer_class, queryset, include_additional_fields, show_display_fields
):
    serializer = serializer_class(
        queryset,
        include_additional_fields=include_additional_fields,
        show_display_fields=show_display_fields,
    )
    return serializer.get_serialized_data() or []

 
def _flatten_column(column_name, column_records):
    all_keys = {f"{column_name}_{key}": key for d in column_records for key in d.keys()}
    return {new_key: [dic.get(key, None) for dic in column_records] for new_key, key in all_keys.items()}


def is_json_like(v):
    return isinstance(v, dict)


def _flatten_json_columns(content):
    headers = content[0]
    cols = list(zip(*[c.values() for c in content[1:]])) # transpose rows
    new_columns = []
    new_headers = []
    existing_headers = []
    existing_columns = []
    for header, col in zip(headers, cols):
        if any(map(is_json_like, col)) is True:
            flattened_columns = _flatten_column(header, col)
            new_headers.extend(list(flattened_columns.keys()))
            new_columns.extend(list(flattened_columns.values()))
        else:
            existing_columns.append(col)
            existing_headers.append(header)
    
    existing_headers.extend(new_headers)
    existing_columns.extend(new_columns)
    return [existing_headers] + list(zip(*existing_columns)) # transpose columns


def _get_csv_response(file_name, fields, data):
    report = RawCSVReport()
    fdata = report.data(fields, data)
    data = _flatten_json_columns(fdata)
    response = StreamingHttpResponse(report.stream_list(data[0], data[1:]), content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{file_name}"'

    return response


def get_csv_response(
    queryset,
    serializer_class,
    file_name_prefix="fieldreport",
    include_additional_fields=False,
    show_display_fields=False,
):
    fields = get_fields(
        serializer_class, include_additional_fields=include_additional_fields, show_display_fields=show_display_fields
    )
    serialized_data = get_data(
        serializer_class, queryset, include_additional_fields=include_additional_fields, show_display_fields=show_display_fields
    )
    serialized_data = list(serialized_data)
    time_stamp = datetime.utcnow().strftime("%Y%m%d")
    file_name = f"{file_name_prefix}-{time_stamp}.csv".lower()
    return _get_csv_response(file_name, fields, serialized_data)
