import logging
import os

import boto3
import botocore
from django.conf import settings

logger = logging.getLogger(__name__)


def get_client(aws_access_key_id=None, aws_secret_access_key=None):
    if aws_access_key_id is None:
        aws_access_key_id = settings.AWS_ACCESS_KEY_ID
    if aws_secret_access_key is None:
        aws_secret_access_key = settings.AWS_SECRET_ACCESS_KEY

    session = boto3.session.Session(
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=settings.AWS_REGION,
    )
    return session.client("s3")


def get_object(bucket, key, aws_access_key_id=None, aws_secret_access_key=None):
    if aws_access_key_id is None:
        aws_access_key_id = settings.AWS_ACCESS_KEY_ID
    if aws_secret_access_key is None:
        aws_secret_access_key = settings.AWS_SECRET_ACCESS_KEY

    client = get_client(
        aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key
    )
    return client.get_object(Bucket=bucket, Key=key)


def delete_file(bucket, blob_name, aws_access_key_id=None, aws_secret_access_key=None):
    if aws_access_key_id is None:
        aws_access_key_id = settings.AWS_ACCESS_KEY_ID
    if aws_secret_access_key is None:
        aws_secret_access_key = settings.AWS_SECRET_ACCESS_KEY

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
    except Exception as e:
        logger.error(f"Error deleting file {blob_name} from bucket {bucket}: {e}")
        return False


def upload_file(
    bucket,
    local_file_path,
    blob_name,
    content_type=None,
    content_encoding=None,
    aws_access_key_id=None,
    aws_secret_access_key=None,
):
    if aws_access_key_id is None:
        aws_access_key_id = settings.AWS_ACCESS_KEY_ID
    if aws_secret_access_key is None:
        aws_secret_access_key = settings.AWS_SECRET_ACCESS_KEY

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
    if aws_access_key_id is None:
        aws_access_key_id = settings.AWS_ACCESS_KEY_ID
    if aws_secret_access_key is None:
        aws_secret_access_key = settings.AWS_SECRET_ACCESS_KEY

    client = get_client(
        aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key
    )
    client.download_file(bucket, blob_name, local_file_path)


def file_exists(bucket, blob_name, aws_access_key_id=None, aws_secret_access_key=None):
    if aws_access_key_id is None:
        aws_access_key_id = settings.AWS_ACCESS_KEY_ID
    if aws_secret_access_key is None:
        aws_secret_access_key = settings.AWS_SECRET_ACCESS_KEY

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


def download_directory(
    bucket, s3_directory, local_directory, aws_access_key_id=None, aws_secret_access_key=None
):
    if aws_access_key_id is None:
        aws_access_key_id = settings.AWS_ACCESS_KEY_ID
    if aws_secret_access_key is None:
        aws_secret_access_key = settings.AWS_SECRET_ACCESS_KEY

    print(bucket)
    print(s3_directory)
    print(aws_access_key_id)
    print(aws_secret_access_key)
    client = get_client(
        aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key
    )
    paginator = client.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=bucket, Prefix=s3_directory)

    for page in pages:
        for obj in page.get("Contents", []):
            s3_key = obj["Key"]
            local_path = os.path.join(local_directory, os.path.relpath(s3_key, s3_directory))
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            if os.path.isdir(local_path):
                continue
            client.download_file(bucket, s3_key, local_path)


def get_presigned_url(
    bucket, key, expiration=604_800, aws_access_key_id=None, aws_secret_access_key=None
):
    if aws_access_key_id is None:
        aws_access_key_id = settings.AWS_ACCESS_KEY_ID
    if aws_secret_access_key is None:
        aws_secret_access_key = settings.AWS_SECRET_ACCESS_KEY

    client = get_client(
        aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key
    )
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expiration,
    )
