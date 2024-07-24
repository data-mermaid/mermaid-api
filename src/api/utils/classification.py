import datetime
import hashlib

import os
from enum import Enum
from io import BytesIO
from typing import Any, Dict, Optional

import pytz
from django.contrib.gis.geos import Point
from django.core.files.base import ContentFile
from django.db.models.fields.files import ImageFieldFile
from exif import Image as ExifImage
from PIL import Image as PILImage
from PIL.ExifTags import TAGS

from ..models import Image
from .encryption import encrypt_string


def create_unique_image_name(image: Image) -> str:
    site = image.site
    if not site:
        raise ValueError(f"No site is related to image {image.id}")

    site_id = str(site.id)
    uid_str = f"{site_id}-{image.id}"

    name = encrypt_string(uid_str)

    image_name = image.image.name
    image_ext = os.path.splitext(image_name)[1]

    return f"{name}{image_ext}"


def create_image_checksum(image: ImageFieldFile) -> str:
    if image.closed:
        image.open("rb")
    file_hash = hashlib.sha256()

    for chunk in image.chunks():
        file_hash.update(chunk)

    return file_hash.hexdigest()


def create_thumbnail(image: ImageFieldFile) -> ContentFile:
    img = PILImage.open(image)
    size = (500, 500)
    img.thumbnail(size, PILImage.LANCZOS)

    base, ext = os.path.splitext(image.name)
    thumb_name = f"{base}_thumbnail{ext}"

    thumb_io = BytesIO()
    try:
        img.save(thumb_io, img.format)
    except IOError as io_err:
        print(f"Cannot create thumbnail for [{image.id}]: {io_err}")
        raise

    return ContentFile(thumb_io.getvalue(), name=thumb_name)


def convert_to_utc(timestamp_str: str) -> datetime:
    local_time = datetime.fromisoformat(timestamp_str)
    return local_time.astimezone(pytz.utc)


def extract_datetime_stamp(exif_details: Dict[str, Any]) -> Optional[datetime.datetime]:
    date_stamp = exif_details.get("gps_datestamp")  # str, 2024:04:06
    time_stamp = exif_details.get("gps_timestamp")  # tuple

    if date_stamp and time_stamp:
        date_stamp = map(int, date_stamp.split(":"))
        time_stamp = map(int, time_stamp)
        return datetime.datetime(*date_stamp, *time_stamp, tzinfo=pytz.UTC)

    date_time_str = exif_details.get("datetime_original")
    offset_time = exif_details.get("offset_time")

    if not date_stamp or not date_time_str or offset_time is None:
        return None

    dt = datetime.datetime.strptime(date_time_str, "%Y:%m:%d %H:%M:%S")
    offset = datetime.timedelta(hours=offset_time)
    local_tz = datetime.timezone(offset)
    dt_local = dt.replace(tzinfo=local_tz)

    return dt_local.astimezone(pytz.UTC)


def extract_location(exif_details: Dict[str, Any]) -> Optional[Point]:
    latitude_ref = exif_details.get("gps_latitude_ref")  # N or S
    latitude_dms = exif_details.get("gps_latitude")  # tuple (DMS)
    longitude_ref = exif_details.get("gps_longitude_ref")  # E or W
    longitude_dms = exif_details.get("gps_longitude")  # tuple (DMS)

    if (
        not all([latitude_ref, latitude_dms, longitude_ref, longitude_dms])
        or len(latitude_dms) < 3
        or len(longitude_dms) < 3
    ):
        return None

    latitude = latitude_dms[0] + latitude_dms[1] / 60 + latitude_dms[2] / 3600
    longitude = longitude_dms[0] + longitude_dms[1] / 60 + longitude_dms[2] / 3600

    latitude *= -1 if latitude_ref == "S" else 1
    longitude *= -1 if longitude_ref == "W" else 1

    return Point(longitude, latitude)


def correct_image_orientation(image_record: Image):
    image_file = PILImage.open(image_record.image)
    image_format = image_file.format
    try:
        for orientation in TAGS.keys():
            if TAGS[orientation] == "Orientation":
                break

        exif = dict(image_file._getexif().items())

        if exif[orientation] == 3:
            image_file = image_file.rotate(180, expand=True)
        elif exif[orientation] == 6:
            image_file = image_file.rotate(270, expand=True)
        elif exif[orientation] == 8:
            image_file = image_file.rotate(90, expand=True)
    except (AttributeError, KeyError, IndexError) as _:
        pass

    img_content = BytesIO()
    image_file.save(img_content, format=image_format)

    image_record.image = ContentFile(img_content.getvalue(), name=image_record.image.name)


def store_exif(image_record: Image) -> Dict[str, Any]:
    img = image_record.image
    if img.closed:
        img.open("rb")

    exif_image = ExifImage(img.read())

    if exif_image.has_exif is False:
        return

    exif_details = {}
    for k, v in exif_image.get_all().items():
        if isinstance(v, Enum):
            v = v.name
        elif isinstance(v, (int, float, tuple, list)):
            ...
        else:
            v = str(v)

        exif_details[k] = v

    image_record.data = image_record.data or {}
    image_record.data["exif"] = exif_details
    image_record.location = extract_location(exif_details)
    image_record.photo_timestamp = extract_datetime_stamp(exif_details)


def create_points(image):
    ...


def classify_image(image_record_id, background=True):
    ...
