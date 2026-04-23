import csv as csv_module
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


_CSV_ROWS = [
    ["protocol", "name", "value"],
    ["beltfish", "Site One", "42"],
]


def _rows_to_bytes(rows):
    buf = io.StringIO()
    csv_module.writer(buf).writerows(rows)
    return buf.getvalue().encode("utf-8")


def _make_view_cls(response):
    class MockView:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
            self.kwargs = {}
            self.request = None

        def csv(self, request, *args, **kwargs):
            return response

    return MockView


def test_get_viewset_csv_content_plain_response():
    csv_bytes = _rows_to_bytes(_CSV_ROWS)
    view_cls = _make_view_cls(StreamingHttpResponse(iter([csv_bytes])))

    with patch("api.reports.summary_report.cached.get_cached_textfile", return_value=None):
        result = list(get_viewset_csv_content(view_cls, "test-pk", None))

    assert result == _CSV_ROWS


def test_get_viewset_csv_content_gzip_response():
    """Viewset returns gzip-encoded content (the cache-hit path in AggregatedViewMixin)."""
    csv_bytes = _rows_to_bytes(_CSV_ROWS)
    response = StreamingHttpResponse(iter([gzip.compress(csv_bytes)]))
    response["Content-Encoding"] = "gzip"
    view_cls = _make_view_cls(response)

    with patch("api.reports.summary_report.cached.get_cached_textfile", return_value=None):
        result = list(get_viewset_csv_content(view_cls, "test-pk", None))

    assert result == _CSV_ROWS


def test_get_viewset_csv_content_cached_file():
    """When get_cached_textfile returns data, it is used directly without calling the viewset."""
    csv_lines = [",".join(row) for row in _CSV_ROWS]

    class MockView:
        def __init__(self, **kwargs):
            pass

        def csv(self, request, *args, **kwargs):
            raise AssertionError("viewset csv should not be called when cache is populated")

    with patch(
        "api.reports.summary_report.cached.get_cached_textfile", return_value=iter(csv_lines)
    ):
        result = list(get_viewset_csv_content(MockView, "test-pk", None))

    assert result == _CSV_ROWS
