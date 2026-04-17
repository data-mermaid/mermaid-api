"""
Data migration: rename EXIF keys stored by the old `exif` library (snake_case)
to PIL CamelCase tag names.

Before M1855, store_exif used the `exif` Python library whose attribute names
differed from PIL's — e.g. PIL uses "DateTimeOriginal" while the exif library
used "datetime_original".  Images uploaded before M1855 have old-format keys
in class_image.data["exif"].  This migration renames those keys in-place; no
S3 access is required.
"""

from django.db import migrations, transaction

# Maps every exif-library attribute name that has appeared in production data
# to its PIL.ExifTags equivalent.  Internal pointer fields (prefixed with _)
# are dropped — they are byte offsets, not meaningful EXIF values.
#
# Where the exif library and PIL use different *semantic* names for the same
# tag (e.g. photographic_sensitivity vs ISOSpeedRatings), the PIL name wins
# because it matches the EXIF spec tag name more closely.
_EXIF_LIB_TO_PIL = {
    # ── dropped internal pointer fields ──────────────────────────────────────
    "_exif_ifd_pointer": None,
    "_gps_ifd_pointer": None,
    # ── datetime / offset ────────────────────────────────────────────────────
    "datetime": "DateTime",
    "datetime_original": "DateTimeOriginal",
    "datetime_digitized": "DateTimeDigitized",
    "offset_time": "OffsetTime",
    "offset_time_original": "OffsetTimeOriginal",
    "offset_time_digitized": "OffsetTimeDigitized",
    "subsec_time": "SubsecTime",
    "subsec_time_original": "SubsecTimeOriginal",
    "subsec_time_digitized": "SubsecTimeDigitized",
    # ── camera identity ───────────────────────────────────────────────────────
    "make": "Make",
    "model": "Model",
    "software": "Software",
    "image_description": "ImageDescription",
    "artist": "Artist",
    "copyright": "Copyright",
    "body_serial_number": "BodySerialNumber",
    "camera_owner_name": "CameraOwnerName",
    "lens_make": "LensMake",
    "lens_model": "LensModel",
    "lens_serial_number": "LensSerialNumber",
    "lens_specification": "LensSpecification",
    "xp_author": "XPAuthor",
    # ── image geometry / resolution ───────────────────────────────────────────
    "orientation": "Orientation",
    "x_resolution": "XResolution",
    "y_resolution": "YResolution",
    "resolution_unit": "ResolutionUnit",
    "y_and_c_positioning": "YCbCrPositioning",
    "pixel_x_dimension": "ExifImageWidth",
    "pixel_y_dimension": "ExifImageHeight",
    "compression": "Compression",
    "compressed_bits_per_pixel": "CompressedBitsPerPixel",
    "jpeg_interchange_format": "JpegIFOffset",
    "jpeg_interchange_format_length": "JpegIFByteCount",
    # ── exposure / photometry ─────────────────────────────────────────────────
    "exposure_time": "ExposureTime",
    "f_number": "FNumber",
    "exposure_program": "ExposureProgram",
    "photographic_sensitivity": "ISOSpeedRatings",
    "sensitivity_type": "SensitivityType",
    "recommended_exposure_index": "RecommendedExposureIndex",
    "shutter_speed_value": "ShutterSpeedValue",
    "aperture_value": "ApertureValue",
    "brightness_value": "BrightnessValue",
    "exposure_bias_value": "ExposureBiasValue",
    "max_aperture_value": "MaxApertureValue",
    "subject_distance": "SubjectDistance",
    "metering_mode": "MeteringMode",
    "light_source": "LightSource",
    "flash": "Flash",
    "focal_length": "FocalLength",
    "exposure_mode": "ExposureMode",
    "white_balance": "WhiteBalance",
    "digital_zoom_ratio": "DigitalZoomRatio",
    "focal_length_in_35mm_film": "FocalLengthIn35mmFilm",
    "scene_capture_type": "SceneCaptureType",
    "gain_control": "GainControl",
    "contrast": "Contrast",
    "saturation": "Saturation",
    "sharpness": "Sharpness",
    "subject_distance_range": "SubjectDistanceRange",
    "custom_rendered": "CustomRendered",
    "exposure_index": "ExposureIndex",
    "sensing_method": "SensingMethod",
    "subject_area": "SubjectLocation",
    # ── colour / rendering ────────────────────────────────────────────────────
    "color_space": "ColorSpace",
    "exif_version": "ExifVersion",
    "user_comment": "UserComment",
    # ── optics ───────────────────────────────────────────────────────────────
    "focal_plane_x_resolution": "FocalPlaneXResolution",
    "focal_plane_y_resolution": "FocalPlaneYResolution",
    "focal_plane_resolution_unit": "FocalPlaneResolutionUnit",
    # ── GPS ──────────────────────────────────────────────────────────────────
    "gps_version_id": "GPSVersionID",
    "gps_latitude_ref": "GPSLatitudeRef",
    "gps_latitude": "GPSLatitude",
    "gps_longitude_ref": "GPSLongitudeRef",
    "gps_longitude": "GPSLongitude",
    "gps_altitude_ref": "GPSAltitudeRef",
    "gps_altitude": "GPSAltitude",
    "gps_timestamp": "GPSTimeStamp",
    "gps_datestamp": "GPSDateStamp",
    "gps_speed_ref": "GPSSpeedRef",
    "gps_speed": "GPSSpeed",
    "gps_img_direction_ref": "GPSImgDirectionRef",
    "gps_img_direction": "GPSImgDirection",
    "gps_dest_bearing_ref": "GPSDestBearingRef",
    "gps_dest_bearing": "GPSDestBearing",
    "gps_horizontal_positioning_error": "GPSHPositioningError",
    "gps_status": "GPSStatus",
}


def _is_old_format(exif_dict: dict) -> bool:
    """Return True if the stored EXIF dict uses old exif-library snake_case keys.

    Underscore-prefixed keys (e.g. '_exif_ifd_pointer') are also treated as legacy.
    Keys that are numeric strings (e.g. '34853', stored as fallback tag IDs by PIL)
    are treated as neither old nor new format and do not trigger migration.
    Empty or non-string keys are skipped safely.
    """
    return any(
        isinstance(k, str)
        and len(k) > 0
        and (k.startswith("_") or (k[0].isalpha() and k[0].islower()))
        for k in exif_dict
    )


def _migrate_exif_dict(exif_dict: dict) -> tuple:
    """Return (migrated_dict, unknown_keys) from exif-lib to PIL CamelCase.

    Explicitly dropped keys (internal pointer fields mapped to None) are silently
    discarded.  Keys not present in _EXIF_LIB_TO_PIL at all are returned separately
    as unknown_keys so callers can log or inspect them.
    """
    result = {}
    unknown = []
    for old_key, value in exif_dict.items():
        if old_key not in _EXIF_LIB_TO_PIL:
            unknown.append(old_key)
            result[old_key] = value
            continue
        new_key = _EXIF_LIB_TO_PIL[old_key]
        if new_key is None:
            continue
        result[new_key] = value
    return result, unknown


def backfill_exif_keys(apps, schema_editor):
    Image = apps.get_model("api", "Image")
    batch_size = 200

    qs = Image.objects.filter(data__has_key="exif").only("id", "data")
    batch = []

    for image in qs.iterator(chunk_size=batch_size):
        exif_dict = image.data.get("exif", {})
        if not isinstance(exif_dict, dict) or not _is_old_format(exif_dict):
            continue

        new_exif, unknown_keys = _migrate_exif_dict(exif_dict)
        if unknown_keys:
            print(
                f"  WARNING {image.pk}: {len(unknown_keys)} unmapped key(s): "
                + ", ".join(repr(k) for k in unknown_keys)
            )

        image.data["exif"] = new_exif
        batch.append(image)

        if len(batch) >= batch_size:
            with transaction.atomic():
                Image.objects.bulk_update(batch, ["data"])
            batch = []

    if batch:
        with transaction.atomic():
            Image.objects.bulk_update(batch, ["data"])


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0103_allow_null_collect_explore_state"),
    ]

    operations = [
        migrations.RunPython(backfill_exif_keys, migrations.RunPython.noop),
    ]
