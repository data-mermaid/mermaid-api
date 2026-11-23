from decimal import ROUND_HALF_DOWN, Decimal, localcontext


def to_number(string, max_digits=None, precision=None):
    if string == "" or string is None:
        return None
    try:
        if max_digits is None or precision is None:
            num = float(string)
            return int(num) if num.is_integer() else num
        else:
            with localcontext() as ctx:
                ctx.prec = max_digits
                places = Decimal(10) ** (precision * -1)
                return Decimal(string).quantize(places, ROUND_HALF_DOWN)
    except (TypeError, ValueError, ArithmeticError):
        return None


# Leading characters a spreadsheet treats as the start of a formula.
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def neutralize_formula(value):
    """Stop CSV/Excel formula injection (CWE-1236). If a string cell starts with a
    character a spreadsheet reads as a formula, prefix a single quote so the value is
    shown literally. Non-strings pass through unchanged."""
    if isinstance(value, str) and value and value[0] in _FORMULA_PREFIXES:
        return "'" + value
    return value


def cast_str_value(s):
    if not isinstance(s, str):
        return s

    val = to_number(s)
    # A numeric string (incl. a legitimate leading "-") becomes a number and needs no
    # neutralizing; only free text that stays a string could carry a formula.
    return val if val is not None else neutralize_formula(s)


def to_yesno(value: bool):
    """
    Casts a boolean value to a "Yes" or "No" string.
    If the value is None, an empty string is returned.
    """
    if value is None:
        return ""

    return "Yes" if value else "No"
