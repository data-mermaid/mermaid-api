from decimal import ROUND_HALF_DOWN, Decimal, localcontext


def to_number(string, max_digits=None, precision=None):
    if str(string) == "" or string is None:
        return None

    if max_digits is None or precision is None:
        try:
            num = float(string)
            return int(num) if num.is_integer() else num
        except (TypeError, ValueError) as e:
            return None

    with localcontext() as ctx:
        ctx.prec = max_digits
        places = Decimal(10) ** (precision * -1)
        return Decimal(string).quantize(places, ROUND_HALF_DOWN)


def cast_str_value(string):
    if not isinstance(string, str):
        return string

    val = to_number(string)
    return val if val is not None else string
