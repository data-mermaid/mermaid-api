from rest_framework.exceptions import ParseError

from ...exceptions import check_uuid


def valid_id(uuid):
    try:
        uuid = check_uuid(uuid)
    except ParseError:
        return None
    return uuid
