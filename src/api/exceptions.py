import uuid

from django.utils.translation import gettext as _
from rest_framework.exceptions import ParseError


class ReadOnlyError(Exception):
    pass


class UpdateSummariesException(Exception):
    def __init__(self, message="Error updating summaries", errors=None):
        super().__init__(message)
        self.errors = errors


def check_uuid(pk):
    if isinstance(pk, uuid.UUID):
        return pk
    try:
        uuid.UUID(pk)
        return pk
    except (ValueError, TypeError, AttributeError):
        raise ParseError(detail=_("'%(value)s' is not a valid uuid") % {"value": pk})
