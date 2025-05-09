import gzip
import hashlib
import logging
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Optional

from django.conf import settings
from django.http import StreamingHttpResponse
from django.utils.encoding import force_bytes

from . import gzip_file, s3

CACHED_PREFIX = f"{settings.ENVIRONMENT}/cached"
IGNORED_QUERY_PARAMS = (
    "token",
    "field_report",
)

logger = logging.getLogger(__name__)


def _cached_text_file(s3_streaming_response):
    try:
        _gzip_file_path = None
        streaming_body = (s3_streaming_response or {}).get("Body")
        if not streaming_body:
            return None

        content_type = s3_streaming_response.get("ContentType")
        if s3_streaming_response.get("ContentEncoding") == "gzip" and content_type.startswith(
            "text/"
        ):
            with NamedTemporaryFile(delete=False, mode="wb") as f:
                _gzip_file_path = f.name
                for chunk in streaming_body.iter_chunks():
                    f.write(chunk)

                f.close()
                with gzip.open(_gzip_file_path, "rt", encoding="utf-8") as gz:
                    for ln in gz:
                        yield ln.strip()

        elif content_type.startswith("text/"):
            yield from streaming_body.iter_lines()

        else:
            raise ValueError(f"Unsupported content type: {content_type}")
    finally:
        if _gzip_file_path and Path(_gzip_file_path).exists():
            Path(_gzip_file_path).unlink()

        if s3_streaming_response and s3_streaming_response.get("Body"):
            s3_streaming_response["Body"].close()


def make_key(*args):
    key = "::".join(str(a) for a in args)
    return hashlib.sha256(force_bytes(key)).hexdigest()


def make_viewset_cache_key(
    viewset_cls, project_id, include_additional_fields=None, show_display_fields=None
):
    c = None
    if hasattr(viewset_cls, "__name__"):
        c = viewset_cls
    else:
        c = viewset_cls.__class__

    return make_key(c.__name__.lower(), project_id, include_additional_fields, show_display_fields)


def full_s3_path(key):
    return f"{CACHED_PREFIX}/{key}"


def cache_file(key, local_file_path, compress=True, content_type=None):
    local_file_path = Path(local_file_path)
    if not local_file_path.exists():
        return False

    _file_path = None
    compress_file_path = None
    if compress:
        compress_file_path = gzip_file(local_file_path, local_file_path.stem)
        _file_path = compress_file_path
    else:
        _file_path = local_file_path

    try:
        s3.upload_file(
            settings.AWS_DATA_BUCKET,
            _file_path,
            full_s3_path(key),
            content_type=content_type,
            content_encoding="gzip" if compress else None,
        )
    finally:
        if compress_file_path and compress_file_path.exists():
            compress_file_path.unlink()


def get_cached_textfile(key):
    s3_obj = _get_file_from_s3(key)
    return _cached_text_file(s3_obj) if s3_obj else None


def _get_file_from_s3(key):
    try:
        if exists(key):
            s3_obj = s3.get_object(settings.AWS_DATA_BUCKET, full_s3_path(key))
            logger.info(f"Content length: {s3_obj['ContentLength']}")
            return s3_obj
        return None
    except Exception as e:
        logger.error(f"Failed to get cached file for key {key}: {e}")
    return None


def delete_file(key):
    s3.delete_file(settings.AWS_DATA_BUCKET, full_s3_path(key))
    return True


def has_filtering_params(request):
    filtering_params = []
    for k in request.query_params:
        if k.lower() in IGNORED_QUERY_PARAMS:
            continue
        else:
            filtering_params.append(k)

    if filtering_params:
        logging.warning(f"Has filtering params: {filtering_params}")
        return True

    return False


def exists(key):
    return s3.file_exists(settings.AWS_DATA_BUCKET, full_s3_path(key))


def _get_or_none(val, fallback, default=None):
    return val if val is not None else fallback or default


def streaming_response(
    request,
    key,
    file_name=None,
    content_type=None,
    content_encoding=None,
    content_disposition="inline",
) -> Optional[StreamingHttpResponse]:
    if has_filtering_params(request) or not exists(key):
        return None

    try:
        s3_obj = s3.get_object(settings.AWS_DATA_BUCKET, full_s3_path(key))
        file_name = file_name or Path(key).stem

        response_args = {
            "headers": {
                "Content-Disposition": f'{content_disposition}; filename="{file_name}"',
            }
        }
        content_type = _get_or_none(content_type, s3_obj.get("ContentType"))
        if content_type:
            response_args["content_type"] = content_type

        content_encoding = _get_or_none(content_encoding, s3_obj.get("ContentEncoding"))
        if content_encoding:
            response_args["headers"]["Content-Encoding"] = content_encoding

        response = StreamingHttpResponse(s3_obj["Body"].iter_chunks(), **response_args)

        return response
    except Exception as e:
        logger.error(f'Failed to create streaming response for key "{key}": {e}')
        return None
