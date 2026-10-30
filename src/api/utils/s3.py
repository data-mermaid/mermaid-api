import json
import os

import boto3
import botocore
from django.conf import settings


def resolve_credentials(aws_access_key_id=None, aws_secret_access_key=None):
    """Return the (access_key, secret_key) pair get_client would use, filling in defaults."""
    return (
        aws_access_key_id or settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key or settings.AWS_SECRET_ACCESS_KEY,
    )


def same_credentials(source_config, dest_config):
    """True when two storage configs resolve to the same AWS credentials, so one client
    can reach both buckets and a server-side copy is possible."""
    return resolve_credentials(
        source_config.get("access_key"), source_config.get("secret_key")
    ) == resolve_credentials(dest_config.get("access_key"), dest_config.get("secret_key"))


def get_client(aws_access_key_id=None, aws_secret_access_key=None):
    aws_access_key_id, aws_secret_access_key = resolve_credentials(
        aws_access_key_id, aws_secret_access_key
    )

    session = boto3.session.Session(
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=settings.AWS_REGION,
    )
    return session.client("s3")


def get_object(bucket, key, aws_access_key_id=None, aws_secret_access_key=None):
    client = get_client(
        aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key
    )
    return client.get_object(Bucket=bucket, Key=key)


def read_json_object(bucket, key, aws_access_key_id=None, aws_secret_access_key=None):
    response = get_object(
        bucket,
        key,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
    )
    return json.loads(response["Body"].read())


def delete_file(bucket, blob_name, aws_access_key_id=None, aws_secret_access_key=None, client=None):
    """Delete blob_name from bucket. Pass a pre-created client to avoid repeated session
    instantiation when deleting many objects in a loop."""
    if client is None:
        client = get_client(
            aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key
        )
    try:
        client.delete_object(Bucket=bucket, Key=blob_name)
        return True
    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            return False
        raise


# delete_objects accepts at most 1000 keys per request.
DELETE_OBJECTS_MAX_KEYS = 1000


def delete_files(
    bucket, blob_names, aws_access_key_id=None, aws_secret_access_key=None, client=None
):
    """Delete blob_names from bucket in batches of up to 1000 keys per request.
    Missing keys are not errors. Returns per-key error dicts ({"Key", "Message"}); a batch
    whose request fails reports each of its keys and later batches are still attempted."""
    blob_names = list(blob_names)
    if not blob_names:
        return []
    if client is None:
        client = get_client(
            aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key
        )

    errors = []
    for i in range(0, len(blob_names), DELETE_OBJECTS_MAX_KEYS):
        batch = blob_names[i : i + DELETE_OBJECTS_MAX_KEYS]
        try:
            response = client.delete_objects(
                Bucket=bucket,
                Delete={"Objects": [{"Key": key} for key in batch], "Quiet": True},
            )
        except (botocore.exceptions.BotoCoreError, botocore.exceptions.ClientError) as e:
            errors.extend({"Key": key, "Message": str(e)} for key in batch)
            continue
        errors.extend(response.get("Errors", []))
    return errors


def upload_file(
    bucket,
    local_file_path,
    blob_name,
    content_type=None,
    content_encoding=None,
    aws_access_key_id=None,
    aws_secret_access_key=None,
):
    client = get_client(
        aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key
    )

    extra_args = {}
    if content_type:
        extra_args["ContentType"] = content_type
    if content_encoding:
        extra_args["ContentEncoding"] = content_encoding

    client.upload_file(local_file_path, bucket, blob_name, ExtraArgs=extra_args)


def download_file(
    bucket, blob_name, local_file_path, aws_access_key_id=None, aws_secret_access_key=None
):
    client = get_client(
        aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key
    )
    client.download_file(bucket, blob_name, local_file_path)


def file_exists(bucket, blob_name, aws_access_key_id=None, aws_secret_access_key=None):
    client = get_client(
        aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key
    )
    try:
        client.head_object(Bucket=bucket, Key=blob_name)
        return True
    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "404":
            return False
        raise


def list_objects(
    bucket,
    prefix=None,
    download_to=None,
    aws_access_key_id=None,
    aws_secret_access_key=None,
):
    """Return all objects in bucket (optionally under prefix), paginated — no 1000-key cap.
    If download_to is given, also download each object to that local directory, preserving
    its path relative to prefix (mirrors the S3 "directory" tree under local_directory)."""
    client = get_client(
        aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key
    )
    paginator = client.get_paginator("list_objects_v2")
    kwargs = {"Bucket": bucket}
    if prefix:
        kwargs["Prefix"] = prefix
    download_root = os.path.abspath(download_to) if download_to else None
    objects = []
    for page in paginator.paginate(**kwargs):
        for obj in page.get("Contents", []):
            objects.append(obj)
            if download_to:
                s3_key = obj["Key"]
                local_path = os.path.abspath(
                    os.path.join(download_root, os.path.relpath(s3_key, prefix or ""))
                )
                if os.path.commonpath([download_root, local_path]) != download_root:
                    continue
                if s3_key.endswith("/"):
                    # Zero-byte S3 directory marker: create the directory rather than
                    # downloading the marker over the top of it as a file.
                    os.makedirs(local_path, exist_ok=True)
                    continue
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                if os.path.isdir(local_path):
                    continue
                client.download_file(bucket, s3_key, local_path)
    return objects


def get_latest_object(bucket, prefix=None, aws_access_key_id=None, aws_secret_access_key=None):
    """Return the object dict (Key/LastModified/...) with the most recent LastModified
    under prefix, or None if there are no matches."""
    objects = list_objects(
        bucket,
        prefix=prefix,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
    )
    if not objects:
        return None
    return max(objects, key=lambda o: o["LastModified"])


def get_presigned_url(
    bucket, key, expiration=604_800, aws_access_key_id=None, aws_secret_access_key=None
):
    client = get_client(
        aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key
    )
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expiration,
    )


def copy_object_server_side(
    source_bucket,
    source_key,
    dest_bucket,
    dest_key,
    aws_access_key_id=None,
    aws_secret_access_key=None,
    client=None,
):
    """Server-side S3 copy — no data transits through the app server.
    Both buckets must be accessible with the same credentials (same account).
    Pass a pre-created client to avoid repeated session instantiation."""
    if client is None:
        client = get_client(
            aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key
        )
    client.copy_object(
        Bucket=dest_bucket,
        CopySource={"Bucket": source_bucket, "Key": source_key},
        Key=dest_key,
    )


def move_file_cross_account(
    source_bucket,
    source_key,
    source_access_key,
    source_secret_key,
    dest_bucket,
    dest_key,
    dest_access_key,
    dest_secret_key,
    delete_source=True,
    source_client=None,
    dest_client=None,
):
    """Move a file between buckets that may require different AWS credentials.
    Pass pre-created clients to avoid repeated session instantiation."""
    if source_client is None:
        source_client = get_client(
            aws_access_key_id=source_access_key, aws_secret_access_key=source_secret_key
        )
    if dest_client is None:
        dest_client = get_client(
            aws_access_key_id=dest_access_key, aws_secret_access_key=dest_secret_key
        )

    response = source_client.get_object(Bucket=source_bucket, Key=source_key)
    body = response["Body"].read()
    content_type = response.get("ContentType", "application/octet-stream")

    dest_client.put_object(Bucket=dest_bucket, Key=dest_key, Body=body, ContentType=content_type)

    if delete_source:
        source_client.delete_object(Bucket=source_bucket, Key=source_key)
