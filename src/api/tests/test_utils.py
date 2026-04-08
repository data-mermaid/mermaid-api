import io
from unittest.mock import MagicMock

from PIL import Image as PILImage

from api.models import BenthicTransect, QuadratCollection, QuadratTransect, SampleUnit
from api.utils import get_subclasses
from api.utils.classification import store_exif


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


def test_store_exif_jpeg():
    # JPEG images raised AttributeError before the fix because PIL's JpegImagePlugin
    # defines __getattr__ that raises for unknown names, so img.read() on the PIL
    # Image object failed. With the fix (reading from file_obj directly) it works.
    with open("api/tests/data/test_image.jpg", "rb") as f:
        jpeg_bytes = f.read()

    instance = _make_instance(jpeg_bytes)
    store_exif(instance)  # must not raise

    assert instance.data is not None
    assert "exif" in instance.data
    assert len(instance.data["exif"]) > 0


def test_store_exif_png():
    # PNG images produce the same observable result before and after the fix:
    # no EXIF is stored (PNGs don't carry JPEG-style EXIF data).
    # Old code: img.read() raises AttributeError, caught by the signal's outer
    #   except-Exception handler — upload still succeeds, no EXIF stored.
    # New code: file_obj.read() returns bytes; ExifImage raises UnpackError on
    #   non-EXIF bytes, caught internally — upload succeeds, no EXIF stored.
    buf = io.BytesIO()
    PILImage.new("RGB", (10, 10)).save(buf, format="PNG")
    png_bytes = buf.getvalue()

    instance = _make_instance(png_bytes)
    store_exif(instance)  # must not raise

    # PNG has no EXIF — store_exif returns early without setting instance.data
    assert instance.data is None
