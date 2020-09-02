def handle_none(default_val=None):
    def decorator(func):
        def wrapper(*args, **kwargs):
            if args[0] is None:
                return default_val

            return func(*args, **kwargs)

        return wrapper

    return decorator


@handle_none()
def to_str(value, field, row, serializer_instance):
    return str(value)


@handle_none()
def to_float(value, field, row, serializer_instance):
    return float(value)


@handle_none()
def to_latitude(value, field, row, serializer_instance):
    return value.y


@handle_none()
def to_longitude(value, field, row, serializer_instance):
    return value.x


@handle_none()
def to_year(value, field, row, serializer_instance):
    return value.year


@handle_none()
def to_month(value, field, row, serializer_instance):
    return value.month


@handle_none()
def to_day(value, field, row, serializer_instance):
    return value.day


@handle_none()
def to_join_list(value, field, row, serializer_instance):
    return ",".join(value)


@handle_none()
def to_governance(value, field, row, serializer_instance):
    vals = []
    for v in value:
        vals.extend(v.split("/"))

    return ",".join(vals)


@handle_none()
def to_observers(value, field, row, serializer_instance):
    vals = [v["name"] for v in value]
    return ",".join(vals)
