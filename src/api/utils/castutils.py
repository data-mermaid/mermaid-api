from datetime import datetime
from decimal import ROUND_HALF_DOWN, Decimal, localcontext


def to_number(string, max_digits=None, precision=None):
    try:
        if max_digits is None or precision is None:
            num = float(string)
            return int(num) if num.is_integer() else num
        else:
            with localcontext() as ctx:
                ctx.prec = max_digits
                places = Decimal(10) ** (precision * -1)
                return Decimal(string).quantize(places, ROUND_HALF_DOWN)
    except (TypeError, ValueError) as _:
        return None


def cast_str_value(string):
    if not isinstance(string, str):
        return string

    val = to_number(string)
    return val if val is not None else string


def iso8601_to_datetime(iso_datetime_str):
    """
    Converts an ISO formatted date or datetime string to a datetime object.

    Args:
    iso_datetime_str (str): A string representing a date or datetime in ISO 8601 format.

    Returns:
    datetime.datetime: A datetime object representing the given date or datetime.
    """

    if not iso_datetime_str:
        return None

    return datetime.fromisoformat(iso_datetime_str)