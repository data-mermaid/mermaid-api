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
