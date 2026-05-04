import csv
import gzip
import io
from unittest.mock import patch

import pytest
from django.http import StreamingHttpResponse

from api.reports.summary_report import _get_project_metadata, get_viewset_csv_content


@pytest.mark.django_db
def test_get_project_metadata_num_sample_units(project1, benthic_lit1):
    rows = _get_project_metadata([project1.pk], {})
    header = rows[0]
    data = rows[1]

    idx = header.index("Number of Sample Units")
    assert data[idx] == 1


# No site_id column — these tests exercise only the early-return / pass-through path.
# The covariate-enrichment and column-filtering branches require a view_cls with
# serializer_class_csv (fields + additional_fields) and are not covered here.
_CSV_ROWS = [
    ["protocol", "name", "value"],
    ["beltfish", "Site One", "42"],
]


def _rows_to_bytes(rows: list[list[str]]) -> bytes:
    buf = io.StringIO()
    csv.writer(buf).writerows(rows)
    return buf.getvalue().encode("utf-8")


def _make_view_cls(
    response: StreamingHttpResponse | None = None,
    csv_side_effect: Exception | None = None,
) -> type:
    class MockView:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
            self.kwargs = {}
            self.request = None

        def csv(self, request, *args, **kwargs):
            if csv_side_effect is not None:
                raise csv_side_effect
            return response

    return MockView


def test_get_viewset_csv_content_plain_response():
    csv_bytes = _rows_to_bytes(_CSV_ROWS)
    view_cls = _make_view_cls(StreamingHttpResponse(iter([csv_bytes])))

    with patch("api.reports.summary_report.cached.get_cached_textfile", return_value=None):
        result = list(get_viewset_csv_content(view_cls, "test-pk", None))

    assert result == _CSV_ROWS


def test_get_viewset_csv_content_gzip_response():
    """Viewset returns gzip-encoded streaming content; verifies gzip decompression."""
    csv_bytes = _rows_to_bytes(_CSV_ROWS)
    response = StreamingHttpResponse(iter([gzip.compress(csv_bytes)]))
    response["Content-Encoding"] = "gzip"
    view_cls = _make_view_cls(response)

    with patch("api.reports.summary_report.cached.get_cached_textfile", return_value=None):
        result = list(get_viewset_csv_content(view_cls, "test-pk", None))

    assert result == _CSV_ROWS


def test_get_viewset_csv_content_non_200_raises():
    response = StreamingHttpResponse(iter([b"error"]), status=500)
    view_cls = _make_view_cls(response)

    with patch("api.reports.summary_report.cached.get_cached_textfile", return_value=None):
        with pytest.raises(ValueError):
            list(get_viewset_csv_content(view_cls, "test-pk", None))


def test_get_viewset_csv_content_cached_file():
    """When get_cached_textfile returns data, it is used directly without calling the viewset."""
    csv_lines = [",".join(row) for row in _CSV_ROWS]
    view_cls = _make_view_cls(
        csv_side_effect=AssertionError("viewset csv should not be called when cache is populated")
    )

    with patch(
        "api.reports.summary_report.cached.get_cached_textfile", return_value=iter(csv_lines)
    ):
        result = list(get_viewset_csv_content(view_cls, "test-pk", None))

    assert result == _CSV_ROWS
