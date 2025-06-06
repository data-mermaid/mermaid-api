from django.http import StreamingHttpResponse
from django.utils import timezone
from django.utils.text import slugify

from api.reports import RawCSVReport


def get_fields(serializer_class, include_additional_fields, show_display_fields):
    serializer = serializer_class(
        include_additional_fields=include_additional_fields,
        show_display_fields=show_display_fields,
    )
    if show_display_fields is True:
        return [f.display for f in serializer.get_fields()]
    else:
        return [f.alias or f.column_path for f in serializer.get_fields()]


def get_data(serializer_class, queryset, include_additional_fields, show_display_fields):
    serializer = serializer_class(
        queryset,
        include_additional_fields=include_additional_fields,
        show_display_fields=show_display_fields,
    )
    return list(serializer.get_serialized_data()) or []


def _flatten_column(column_name, column_records, separator="_"):
    column_records = [d if d is not None else {} for d in column_records]
    all_keys = {f"{column_name}{separator}{key}": key for d in column_records for key in d.keys()}
    return {new_key: [dic.get(key) for dic in column_records] for new_key, key in all_keys.items()}


def is_json_like(v):
    return isinstance(v, dict)


def _flatten_json_columns(content, show_display_fields=False):
    headers = content[0]

    content_size = len(content)
    if content_size == 0:
        return []
    elif content_size == 1:
        return [headers]

    cols = list(zip(*[c.values() for c in content[1:]]))  # transpose rows
    new_columns = []
    new_headers = []
    existing_headers = []
    existing_columns = []
    separator = ": " if show_display_fields else "_"
    for header, col in zip(headers, cols):
        if any(map(is_json_like, col)) is True:
            flattened_columns = _flatten_column(header, col, separator)
            new_headers.extend(list(flattened_columns.keys()))
            new_columns.extend(list(flattened_columns.values()))
        else:
            existing_columns.append(col)
            existing_headers.append(header)

    existing_headers.extend(new_headers)
    existing_columns.extend(new_columns)
    return [existing_headers] + list(zip(*existing_columns))  # transpose columns


def get_formatted_data(
    data, serializer_class, include_additional_fields=False, show_display_fields=False
):
    fields = get_fields(
        serializer_class,
        include_additional_fields=include_additional_fields,
        show_display_fields=show_display_fields,
    )
    serialized_data = get_data(
        serializer_class,
        data,
        include_additional_fields=include_additional_fields,
        show_display_fields=show_display_fields,
    )
    report = RawCSVReport()
    fdata = report.data(fields, serialized_data)
    formatted_data = _flatten_json_columns(fdata, show_display_fields=show_display_fields)
    return formatted_data[0], formatted_data[1:]


def get_csv_response(
    queryset,
    serializer_class,
    file_name_prefix="fieldreport",
    include_additional_fields=False,
    show_display_fields=False,
):
    time_stamp = timezone.now().strftime("%Y%m%d")
    file_name = f"{slugify(file_name_prefix)}-{time_stamp}.csv"

    columns, rows = get_formatted_data(
        queryset,
        serializer_class,
        include_additional_fields=include_additional_fields,
        show_display_fields=show_display_fields,
    )

    response = StreamingHttpResponse(
        RawCSVReport().stream_list(columns, rows), content_type="text/csv"
    )
    response["Content-Disposition"] = f'attachment; filename="{file_name}"'

    return response
