from decimal import ROUND_HALF_DOWN, Decimal, localcontext


def to_decimal(val, max_digits, precision):
    if str(val) == "" or val is None:
        return None

    with localcontext() as ctx:
        ctx.prec = max_digits
        places = Decimal(10) ** (precision * -1)
        return Decimal(val).quantize(places, ROUND_HALF_DOWN)


def to_number(string):
    try:
        num = float(string)
        return int(num) if num.is_integer() else num
    except ValueError:
        return None


def cast_str_value(string):
    if not isinstance(string, str):
        return string

    val = to_number(string)
    return val if val is not None else string
    