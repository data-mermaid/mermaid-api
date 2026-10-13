import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from api.models import Classifier, Image


@pytest.fixture
def image(valid_benthic_pq_transect_collect_record):
    with open("api/tests/data/test_image.jpg", "rb") as f:
        content = f.read()

    image_file = SimpleUploadedFile(
        name="test_image.jpg", content=content, content_type="image/jpeg"
    )

    return Image.objects.create(
        collect_record_id=valid_benthic_pq_transect_collect_record.pk,
        image=image_file,
        name="Test image",
    )


@pytest.fixture
def classifier():
    return Classifier.objects.create(
        name="Test classifier", version="v0", config={"patch_size": 144}
    )


@pytest.fixture
def classifier_v2():
    return Classifier.objects.create(
        name="Test classifier", version="v2", config={"patch_size": 144}
    )


@pytest.fixture
def stub_manifest(monkeypatch):
    """Patch the S3 JSON read; return a setter the test calls with a manifest dict.

    The setter's `.calls` attribute records each (bucket, key) the read was called with.
    """
    holder = {}
    calls = []

    def fake_read_json_object(bucket, key, *args, **kwargs):
        calls.append((bucket, key))
        return holder["manifest"]

    monkeypatch.setattr("api.utils.s3.read_json_object", fake_read_json_object)

    def set_manifest(manifest):
        holder["manifest"] = manifest

    set_manifest.calls = calls
    return set_manifest
