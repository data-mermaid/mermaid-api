import os

import boto3
from django.conf import settings


def get_client():
    session = boto3.session.Session(
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )
    return session.client("s3")


def upload_file(bucket, local_file_path, blob_name):
    client = get_client()
    client.upload_file(local_file_path, bucket, blob_name)


def download_file(bucket, blob_name, local_file_path):
    client = get_client()
    client.download_file(bucket, blob_name, local_file_path)


def download_directory(bucket, s3_directory, local_directory):
    client = get_client()
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


def get_presigned_url(bucket, key, expiration=604_800):
    client = get_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expiration,
    )
