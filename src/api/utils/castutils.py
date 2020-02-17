from decimal import ROUND_HALF_DOWN, Decimal, localcontext


def to_decimal(val, max_digits, precision):
    if str(val) == "" or val is None:
        return None

    with localcontext() as ctx:
        ctx.prec = max_digits
        places = Decimal(10) ** (precision * -1)
        return Decimal(val).quantize(places, ROUND_HALF_DOWN)
