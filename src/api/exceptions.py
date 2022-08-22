import uuid
from django.utils.translation import gettext as _
from rest_framework.exceptions import ParseError


def check_uuid(pk):
    if isinstance(pk, uuid.UUID):
        return pk
    try:
        uuid.UUID(pk)
        return pk
    except (ValueError, TypeError, AttributeError):
        raise ParseError(
            detail=_("'%(value)s' is not a valid uuid") % {'value': pk}
        )
