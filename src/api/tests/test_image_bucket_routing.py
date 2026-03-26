import io
from unittest.mock import MagicMock, patch

import pytest
from django.core.files.storage import Storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from api.models import Image, Project
from api.models.classification import (
    get_image_bucket,
    get_image_bucket_for_status,
    get_image_storage_config,
)

# ---------------------------------------------------------------------------
# In-memory storage that segregates files by bucket name.
# Shared across all instances via the class-level dict so that a file saved
# by test-bucket storage can only be read back by test-bucket storage (and
# not by prod-bucket storage).  This lets us prove that the post_save signal
# correctly re-applies per-instance storage before reading the image back.
# ---------------------------------------------------------------------------

_BUCKET_FILES: dict = {}


class ReopenableFile:
    """
    Minimal in-memory file-like object that supports Django's FieldFile
    contract: close() followed by open() must work.  BytesIO cannot be
    reopened after close(), which causes Django's FieldFile.open() to crash.
    """

    def __init__(self, data: bytes):
        self._data = data
        self._buf = io.BytesIO(data)
        self._closed = False

    # --- re-open support (called by FieldFile.open() on a closed file) ---
    def open(self, mode=None):
        self._buf = io.BytesIO(self._data)
        self._closed = False
        return self

    # --- standard file-like interface ---
    def read(self, size=-1):
        return self._buf.read(size)

    def seek(self, pos, whence=0):
        return self._buf.seek(pos, whence)

    def tell(self):
        return self._buf.tell()

    def close(self):
        self._closed = True
        self._buf.close()

    @property
    def closed(self):
        return self._closed

    # --- Django File / FieldFile helpers ---
    def chunks(self, chunk_size=8192):
        self.seek(0)
        while True:
            chunk = self.read(chunk_size)
            if not chunk:
                break
            yield chunk

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class BucketMemoryStorage(Storage):
    """Simple in-memory S3 stand-in that segregates files by bucket_name."""

    def __init__(self, bucket_name="", location="", access_key=None, secret_key=None, **kwargs):
        self.bucket_name = bucket_name
        self.location = location

    def _save(self, name, content):
        _BUCKET_FILES[(self.bucket_name, name)] = b"".join(content.chunks())
        return name

    def _open(self, name, mode="rb"):
        key = (self.bucket_name, name)
        if key not in _BUCKET_FILES:
            raise OSError(f"File does not exist: {self.location}{name}")
        return ReopenableFile(_BUCKET_FILES[key])

    def exists(self, name):
        return (self.bucket_name, name) in _BUCKET_FILES

    def url(self, name):
        return f"https://{self.bucket_name}/{self.location}{name}"

    def size(self, name):
        key = (self.bucket_name, name)
        if key in _BUCKET_FILES:
            return len(_BUCKET_FILES[key])
        raise OSError(f"File does not exist: {self.location}{name}")

    def delete(self, name):
        _BUCKET_FILES.pop((self.bucket_name, name), None)

    def path(self, name):
        raise NotImplementedError("BucketMemoryStorage does not support path()")


BUCKET_SETTINGS = {
    "IMAGE_PROCESSING_BUCKET": "prod-bucket",
    "IMAGE_PROCESSING_BUCKET_TEST": "test-bucket",
}

STORAGE_SETTINGS = {
    **BUCKET_SETTINGS,
    "IMAGE_BUCKET_AWS_ACCESS_KEY_ID": "image-key",
    "IMAGE_BUCKET_AWS_SECRET_ACCESS_KEY": "image-secret",
    "AWS_ACCESS_KEY_ID": "default-key",
    "AWS_SECRET_ACCESS_KEY": "default-secret",
    "IMAGE_S3_PATH": "mermaid/",
    "IMAGE_S3_PATH_TEST": "mermaid-production-test/",
}


@pytest.fixture(autouse=True)
def no_s3():
    with patch("api.utils.s3.get_client") as mock:
        mock.return_value = MagicMock()
        yield mock


# --- get_image_bucket ---


@override_settings(**BUCKET_SETTINGS)
@pytest.mark.parametrize(
    "status,expected",
    [
        (Project.TEST, "test-bucket"),
        (Project.OPEN, "prod-bucket"),
    ],
)
def test_get_image_bucket(status, expected):
    project = MagicMock()
    project.status = status
    assert get_image_bucket(project) == expected


@override_settings(**BUCKET_SETTINGS)
def test_get_image_bucket_none_project():
    assert get_image_bucket(None) == "prod-bucket"


@override_settings(
    IMAGE_PROCESSING_BUCKET="same-bucket",
    IMAGE_PROCESSING_BUCKET_TEST="same-bucket",
)
def test_get_image_bucket_dev_like_same_bucket():
    """In dev, both buckets are the same regardless of project status."""
    test_project = MagicMock()
    test_project.status = Project.TEST
    open_project = MagicMock()
    open_project.status = Project.OPEN
    assert get_image_bucket(test_project) == get_image_bucket(open_project)


# --- get_image_bucket_for_status ---


@override_settings(**BUCKET_SETTINGS)
@pytest.mark.parametrize(
    "status,expected",
    [
        (Project.TEST, "test-bucket"),
        (Project.OPEN, "prod-bucket"),
        (Project.LOCKED, "prod-bucket"),
    ],
)
def test_get_image_bucket_for_status(status, expected):
    assert get_image_bucket_for_status(status) == expected


# --- get_image_storage_config ---


@override_settings(**STORAGE_SETTINGS)
@pytest.mark.parametrize(
    "bucket,expected_key,expected_secret,expected_path",
    [
        ("prod-bucket", "image-key", "image-secret", "mermaid/"),
        ("test-bucket", "default-key", "default-secret", "mermaid-production-test/"),
    ],
)
def test_get_image_storage_config(bucket, expected_key, expected_secret, expected_path):
    config = get_image_storage_config(bucket)
    assert config["bucket"] == bucket
    assert config["access_key"] == expected_key
    assert config["secret_key"] == expected_secret
    assert config["s3_path"] == expected_path


@override_settings(
    IMAGE_PROCESSING_BUCKET="same-bucket",
    IMAGE_PROCESSING_BUCKET_TEST="same-bucket",
    IMAGE_BUCKET_AWS_ACCESS_KEY_ID="image-key",
    IMAGE_BUCKET_AWS_SECRET_ACCESS_KEY="image-secret",
    IMAGE_S3_PATH="mermaid/",
    IMAGE_S3_PATH_TEST="mermaid/",
)
def test_get_image_storage_config_dev_like_same_bucket():
    """When buckets are the same (dev), always uses production creds path."""
    config = get_image_storage_config("same-bucket")
    assert config["bucket"] == "same-bucket"
    assert config["access_key"] == "image-key"
    assert config["secret_key"] == "image-secret"


@override_settings(**STORAGE_SETTINGS)
@pytest.mark.parametrize("bucket", [None, ""])
def test_get_image_storage_config_falsy_bucket(bucket):
    """None/empty bucket falls back to production config."""
    config = get_image_storage_config(bucket)
    assert config["bucket"] == "prod-bucket"
    assert config["access_key"] == "image-key"


# --- _get_image_location ---


@override_settings(ENVIRONMENT="dev", **STORAGE_SETTINGS)
@pytest.mark.parametrize(
    "bucket,expected_prefix",
    [
        ("test-bucket", "mermaid-production-test/"),
        ("prod-bucket", "mermaid/"),
    ],
)
def test_get_image_location(bucket, expected_prefix):
    from api.utils.classification import _get_image_location

    image = MagicMock()
    image.image_bucket = bucket
    image.image.name = "abc123.png"

    location = _get_image_location(image)
    assert location.storage_type == "s3"
    assert location.bucket_name == bucket
    assert location.key == f"{expected_prefix}abc123.png"


# --- move_file_cross_account ---


def test_move_file_cross_account(no_s3):
    from api.utils.s3 import move_file_cross_account

    source_client = MagicMock()
    dest_client = MagicMock()
    no_s3.side_effect = [source_client, dest_client]

    source_client.get_object.return_value = {
        "Body": MagicMock(read=lambda: b"image-data"),
        "ContentType": "image/png",
    }

    move_file_cross_account(
        source_bucket="src-bucket",
        source_key="mermaid/img.png",
        source_access_key="src-key",
        source_secret_key="src-secret",
        dest_bucket="dst-bucket",
        dest_key="mermaid-test/img.png",
        dest_access_key="dst-key",
        dest_secret_key="dst-secret",
    )

    source_client.get_object.assert_called_once_with(Bucket="src-bucket", Key="mermaid/img.png")
    dest_client.put_object.assert_called_once_with(
        Bucket="dst-bucket",
        Key="mermaid-test/img.png",
        Body=b"image-data",
        ContentType="image/png",
    )
    source_client.delete_object.assert_called_once_with(Bucket="src-bucket", Key="mermaid/img.png")


# ---------------------------------------------------------------------------
# Regression test: post_save re-applies correct storage after FieldFile.save
# resets instance.image to a plain string (losing the custom storage).
# ---------------------------------------------------------------------------

PROD_LIKE_SETTINGS = {
    "ENVIRONMENT": "prod",
    "IMAGE_PROCESSING_BUCKET": "prod-bucket",
    "IMAGE_PROCESSING_BUCKET_TEST": "test-bucket",
    "IMAGE_S3_PATH": "mermaid/",
    "IMAGE_S3_PATH_TEST": "mermaid-production-test/",
    "IMAGE_BUCKET_AWS_ACCESS_KEY_ID": "image-key",
    "IMAGE_BUCKET_AWS_SECRET_ACCESS_KEY": "image-secret",
    "AWS_ACCESS_KEY_ID": "default-key",
    "AWS_SECRET_ACCESS_KEY": "default-secret",
}


@pytest.mark.django_db
@override_settings(**PROD_LIKE_SETTINGS)
@patch("api.models.classification.S3Storage", BucketMemoryStorage)
def test_test_project_image_upload_uses_test_bucket_storage(
    valid_benthic_pq_transect_collect_record,
):
    """
    Regression: When creating an Image for a test project in a prod-like
    environment (two distinct S3 buckets), the post_save signal must
    re-apply per-instance storage *before* reading the image back.

    Without the fix, FileField.pre_save saves the file to the test bucket but
    then resets instance.image to a plain string.  The next getattr creates a
    new FieldFile backed by the *default* (prod) bucket storage, and
    image.open() raises "File does not exist" because the file is in the test
    bucket.  The exception propagates through Image.objects.create() and the
    view returns a 422.

    With the fix, post_save_classification_image calls instance._apply_storage()
    before touching the image, so the correct bucket is used for both write and
    read.
    """
    _BUCKET_FILES.clear()

    with open("api/tests/data/test_image.jpg", "rb") as f:
        content = f.read()

    image_file = SimpleUploadedFile(
        name="test_image.jpg", content=content, content_type="image/jpeg"
    )

    # This must not raise "File does not exist: mermaid/<uuid>.png"
    image = Image.objects.create(
        collect_record_id=valid_benthic_pq_transect_collect_record.pk,
        image=image_file,
        image_bucket="test-bucket",
    )

    # The image file was saved to and thumbnail read from the test bucket
    saved_buckets = {bucket for bucket, _ in _BUCKET_FILES}
    assert "test-bucket" in saved_buckets, "Image should be stored in the test bucket"
    assert "prod-bucket" not in saved_buckets, "Image should NOT be stored in the prod bucket"

    # The model record reflects the test bucket
    assert image.image_bucket == "test-bucket"
    assert image.thumbnail, "Thumbnail should have been created without error"
