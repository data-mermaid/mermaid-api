import datetime
import io
import pathlib
import struct
import zlib
from fractions import Fraction
from unittest.mock import MagicMock

import pytest
from PIL import Image as PILImage

from api.models import BenthicTransect, QuadratCollection, QuadratTransect, SampleUnit
from api.utils import get_subclasses
from api.utils.classification import (
    _normalize_exif_value,
    extract_datetime_stamp,
    extract_location,
    store_exif,
)

_DATA_DIR = pathlib.Path(__file__).resolve().parent / "data"


def test_get_subclasses():
    subclasses = list(get_subclasses(SampleUnit))
    assert BenthicTransect in subclasses
    assert QuadratTransect in subclasses
    assert QuadratCollection in subclasses


def _make_instance(file_bytes):
    """Minimal Image-like object sufficient for store_exif."""
    file_obj = io.BytesIO(file_bytes)
    instance = MagicMock()
    instance.image.file = file_obj
    instance.data = None
    return instance


def _make_png_with_exif(exif_bytes):
    """Build a minimal PNG containing an eXIf chunk from the given raw EXIF bytes."""
    base = io.BytesIO()
    PILImage.new("RGB", (10, 10)).save(base, format="PNG")
    base_png = base.getvalue()

    def png_chunk(chunk_type, data):
        body = chunk_type + data
        return (
            struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
        )

    iend_pos = base_png.rfind(b"IEND")
    return base_png[: iend_pos - 4] + png_chunk(b"eXIf", exif_bytes) + base_png[iend_pos - 4 :]


def test_store_exif_jpeg():
    # EXIF is extracted from a JPEG and stored with PIL CamelCase tag names.
    jpeg_bytes = (_DATA_DIR / "test_image.jpg").read_bytes()

    instance = _make_instance(jpeg_bytes)
    store_exif(instance)

    assert instance.data is not None
    assert "exif" in instance.data
    assert "DateTimeOriginal" in instance.data["exif"]
    assert instance.data["exif"]["Make"].strip() == "OLYMPUS CORPORATION"


def test_store_exif_jpeg_sets_location_and_timestamp():
    # Verify store_exif writes location and photo_timestamp, not just data["exif"].
    # The fixture JPEG has DateTimeOriginal + OffsetTime but no GPS lat/lon, so
    # photo_timestamp is populated and location is None.
    jpeg_bytes = (_DATA_DIR / "test_image.jpg").read_bytes()
    instance = _make_instance(jpeg_bytes)
    instance.location = None
    instance.photo_timestamp = None
    store_exif(instance)

    assert instance.photo_timestamp is not None
    assert instance.location is None


def test_store_exif_png_no_exif():
    # Plain PNG (no eXIf chunk): store_exif returns early, nothing stored.
    buf = io.BytesIO()
    PILImage.new("RGB", (10, 10)).save(buf, format="PNG")

    instance = _make_instance(buf.getvalue())
    store_exif(instance)

    assert instance.data is None


def test_store_exif_png_with_exif_chunk():
    # PNG with an eXIf chunk: EXIF is extracted, which was impossible with the
    # old exif library since it only understood JPEG byte streams.
    jpeg_bytes = (_DATA_DIR / "test_image.jpg").read_bytes()
    with PILImage.open(io.BytesIO(jpeg_bytes)) as img:
        exif_bytes = img.info.get("exif", b"")
    assert exif_bytes, "test JPEG must carry EXIF data for this fixture to be valid"

    instance = _make_instance(_make_png_with_exif(exif_bytes))
    instance.location = None
    instance.photo_timestamp = None
    store_exif(instance)

    assert instance.data is not None
    assert "exif" in instance.data
    assert "DateTimeOriginal" in instance.data["exif"]
    # Same fixture EXIF bytes as test_store_exif_jpeg: timestamp set, no GPS lat/lon.
    assert instance.photo_timestamp is not None
    assert instance.location is None


def test_extract_datetime_stamp_gps_priority():
    # GPS date+time (UTC) takes priority over EXIF datetime+offset.
    gps_ifd = {29: "2024:04:06", 7: (10, 30, 0)}  # datestamp, timestamp
    exif_ifd = {36867: "2024:04:06 23:30:00", 36880: "+13:00"}

    result = extract_datetime_stamp(exif_ifd, gps_ifd)
    assert result == datetime.datetime(2024, 4, 6, 10, 30, 0, tzinfo=datetime.timezone.utc)


def test_extract_datetime_stamp_offset_fallback():
    # Without GPS time, falls back to EXIF datetime + UTC offset string.
    exif_ifd = {36867: "2017:09:06 10:17:33", 36880: "+13:00"}
    gps_ifd = {}

    result = extract_datetime_stamp(exif_ifd, gps_ifd)
    expected = datetime.datetime(2017, 9, 5, 21, 17, 33, tzinfo=datetime.timezone.utc)
    assert result == expected


def test_extract_datetime_stamp_empty_ifds():
    # Both IFDs empty → None.
    assert extract_datetime_stamp({}, {}) is None


def test_extract_datetime_stamp_no_offset():
    # date_time_str present but offset_str missing → None.
    exif_ifd = {36867: "2017:09:06 10:17:33"}  # no OffsetTime key
    assert extract_datetime_stamp(exif_ifd, {}) is None


def test_extract_datetime_stamp_offset_time_original():
    # Cameras that write OffsetTimeOriginal (36881) but not OffsetTime (36880)
    # must still produce a correct UTC timestamp.
    exif_ifd = {36867: "2017:09:06 10:17:33", 36881: "+13:00"}  # OffsetTimeOriginal only
    result = extract_datetime_stamp(exif_ifd, {})
    assert result == datetime.datetime(2017, 9, 5, 21, 17, 33, tzinfo=datetime.timezone.utc)


def test_extract_datetime_stamp_malformed_gps_falls_through():
    # Malformed GPS timestamp triggers except and falls through to EXIF fallback.
    gps_ifd = {29: "not-a-date", 7: ("bad", "data", "here")}
    exif_ifd = {36867: "2017:09:06 10:17:33", 36880: "+00:00"}

    result = extract_datetime_stamp(exif_ifd, gps_ifd)
    assert result == datetime.datetime(2017, 9, 6, 10, 17, 33, tzinfo=datetime.timezone.utc)


def test_extract_location():
    # Fraction has .numerator so satisfies the IFDRational duck-type check.
    # 36°0'0"N, 139°41'0"E → (36.0, 139.6833...)
    lat = (Fraction(36), Fraction(0), Fraction(0))
    lon = (Fraction(139), Fraction(41), Fraction(0))
    gps_ifd = {1: "N", 2: lat, 3: "E", 4: lon}

    point = extract_location(gps_ifd)
    assert point is not None
    assert abs(point.y - 36.0) < 0.0001  # latitude
    assert abs(point.x - 139.6833) < 0.001  # longitude


def test_extract_location_southern_western_hemisphere():
    # S and W references must negate the computed decimal degrees.
    # 18°S, 147°E (Great Barrier Reef area) and then flip to W for longitude.
    lat = (Fraction(18), Fraction(0), Fraction(0))
    lon = (Fraction(147), Fraction(30), Fraction(0))
    gps_ifd = {1: "S", 2: lat, 3: "W", 4: lon}

    point = extract_location(gps_ifd)
    assert point is not None
    assert point.y < 0  # south → negative latitude
    assert abs(point.y - (-18.0)) < 0.0001
    assert point.x < 0  # west → negative longitude
    assert abs(point.x - (-147.5)) < 0.0001


def test_extract_location_missing_fields():
    # Missing any required GPS field → None.
    assert extract_location({}) is None
    assert extract_location({1: "N", 2: (Fraction(1), Fraction(0), Fraction(0))}) is None


def test_store_exif_tiff():
    # TIFF images did not work with the old exif library at all; PIL handles them.
    # A plain synthetic TIFF has no photographic EXIF sub-IFD so getexif() returns
    # only basic TIFF structural tags — store_exif stores those and doesn't raise.
    buf = io.BytesIO()
    PILImage.new("RGB", (10, 10)).save(buf, format="TIFF")

    instance = _make_instance(buf.getvalue())
    store_exif(instance)  # must not raise
    assert instance.data is not None  # plain TIFF has structural tags stored
    assert isinstance(instance.data.get("exif"), dict)
    assert len(instance.data["exif"]) > 0


@pytest.mark.parametrize(
    "value, expected",
    [
        (b"\x00\xff", None),  # bytes → dropped
        (Fraction(3, 2), 1.5),  # IFDRational-like (has .numerator) → float
        ((Fraction(1), Fraction(2)), (1.0, 2.0)),  # tuple of rationals → tuple of floats
        ((None, None), None),  # tuple where all elements normalize to None → None
        ("hello\x00", "hello"),  # str → stripped null bytes
        ("  padded  ", "padded"),  # str → stripped whitespace
        (42, 42),  # int → pass-through (not converted to float)
        (3.14, 3.14),  # float → pass-through
        ({"nested": "dict"}, None),  # unexpected type → None
    ],
)
def test_normalize_exif_value(value, expected):
    result = _normalize_exif_value(value)
    assert result == expected
    if expected is not None:
        assert type(result) is type(expected)  # 42 must stay int, not become 42.0
