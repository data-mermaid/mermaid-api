from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from api.models import Project
from api.models.classification import (
    get_image_bucket,
    get_image_bucket_for_status,
    get_image_storage_config,
)

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
