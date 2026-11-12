import logging

from api.log_filters import IgnoreGDALJSONParseErrors


def _record(msg):
    return logging.LogRecord(
        name="django.contrib.gis",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg=msg,
        args=None,
        exc_info=None,
    )


def test_drops_json_parsing_error():
    f = IgnoreGDALJSONParseErrors()
    assert f.filter(_record("GDAL_ERROR 4: b'JSON parsing error: unexpected end of data'")) is False


def test_drops_unsupported_geometry_type():
    f = IgnoreGDALJSONParseErrors()
    msg = "GDAL_ERROR 1: b'Unsupported geometry type detected. Feature gets NULL geometry assigned.'"
    assert f.filter(_record(msg)) is False


def test_keeps_other_gdal_errors():
    f = IgnoreGDALJSONParseErrors()
    assert f.filter(_record("GDAL_ERROR 1: b'Something else went wrong'")) is True


def test_keeps_non_gdal_messages():
    f = IgnoreGDALJSONParseErrors()
    assert f.filter(_record("Unsupported geometry type detected")) is True
