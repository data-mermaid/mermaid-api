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


def cast_str_value(s):
    if not isinstance(s, str):
        return s

    val = to_number(s)
    return val if val is not None else s


def to_yesno(value: bool):
    """
    Casts a boolean value to a "Yes" or "No" string.
    If the value is None, an empty string is returned.
    """
    if value is None:
        return ""

    return "Yes" if value else "No"
