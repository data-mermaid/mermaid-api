from io import BytesIO
from tempfile import NamedTemporaryFile

from django.conf import settings

from . import s3
from ..reports import attributes_report


def update_attributes_report():
    with NamedTemporaryFile() as tmp:
        attributes_report.write_attribute_reference(tmp.name)
        s3.upload_file(settings.PUBLIC_BUCKET, tmp.name, "attributes_guide.xlsx")
