import datetime
import io
import struct
import zlib
from fractions import Fraction
from unittest.mock import MagicMock

from PIL import Image as PILImage

from api.models import BenthicTransect, QuadratCollection, QuadratTransect, SampleUnit
from api.utils import get_subclasses
from api.utils.classification import extract_datetime_stamp, extract_location, store_exif


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
    with open("api/tests/data/test_image.jpg", "rb") as f:
        jpeg_bytes = f.read()

    instance = _make_instance(jpeg_bytes)
    store_exif(instance)

    assert instance.data is not None
    assert "exif" in instance.data
    assert "DateTimeOriginal" in instance.data["exif"]
    assert instance.data["exif"]["Make"].strip() == "OLYMPUS CORPORATION"


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
    with open("api/tests/data/test_image.jpg", "rb") as f:
        jpeg_bytes = f.read()
    exif_bytes = PILImage.open(io.BytesIO(jpeg_bytes)).info.get("exif", b"")
    assert exif_bytes, "test JPEG must carry EXIF data for this fixture to be valid"

    instance = _make_instance(_make_png_with_exif(exif_bytes))
    store_exif(instance)

    assert instance.data is not None
    assert "exif" in instance.data
    assert "DateTimeOriginal" in instance.data["exif"]


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


def test_store_exif_tiff():
    # TIFF images did not work with the old exif library at all; PIL handles them.
    # A plain synthetic TIFF has no photographic EXIF sub-IFD so getexif() returns
    # only basic TIFF structural tags — store_exif stores those and doesn't raise.
    buf = io.BytesIO()
    PILImage.new("RGB", (10, 10)).save(buf, format="TIFF")

    instance = _make_instance(buf.getvalue())
    store_exif(instance)  # must not raise
