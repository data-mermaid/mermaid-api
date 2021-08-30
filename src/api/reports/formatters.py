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

    return ", ".join(vals)


@handle_none()
def to_names(value, field, row, serializer_instance):
    vals = [v["name"] for v in value]
    return ", ".join(vals)


@handle_none()
def to_protocol_value(value, field, row, serializer_instance):
    if (
        not hasattr(field, "protocol")
        or not hasattr(field, "key")
        or field.protocol not in value
        or field.key not in value[field.protocol]
    ):
        return None

    returnval = value[field.protocol][field.key]
    if isinstance(returnval, dict):
        returnval = ", ".join([f"{key}: {val}" for key, val in returnval.items()])
    return returnval


@handle_none()
def to_colonies_bleached(value, field, row, serializer_instance):
    if "colonies_bleached" not in value:
        return None

    field.protocol = "colonies_bleached"
    field.key = "count_genera_avg"
    count_genera_avg = to_protocol_value(value, field, row, serializer_instance)
    field.key = "percent_normal_avg"
    percent_normal_avg = to_protocol_value(value, field, row, serializer_instance)
    field.key = "percent_pale_avg"
    percent_pale_avg = to_protocol_value(value, field, row, serializer_instance)
    field.key = "percent_bleached_avg"
    percent_bleached_avg = to_protocol_value(value, field, row, serializer_instance)

    return f"Average genera count: {count_genera_avg}, Average normal %: {percent_normal_avg}, " \
           f"Average pale %: {percent_pale_avg}, Average bleached %: {percent_bleached_avg}"


@handle_none()
def to_percent_cover(value, field, row, serializer_instance):
    if "quadrat_benthic_percent" not in value:
        return None

    field.protocol = "quadrat_benthic_percent"
    field.key = "percent_hard_avg_avg"
    percent_hard_avg_avg = to_protocol_value(value, field, row, serializer_instance)
    field.key = "percent_soft_avg_avg"
    percent_soft_avg_avg = to_protocol_value(value, field, row, serializer_instance)
    field.key = "percent_algae_avg_avg"
    percent_algae_avg_avg = to_protocol_value(value, field, row, serializer_instance)
    field.key = "quadrat_count_avg"
    quadrat_count_avg = to_protocol_value(value, field, row, serializer_instance)

    return f"Average quadrat count: {quadrat_count_avg}, Average hard coral %: {percent_hard_avg_avg}, " \
           f"Average soft coral %: {percent_soft_avg_avg}, Average macroalgae %: {percent_algae_avg_avg}"


def to_covariate(value, field, row, serializer_instance):
    if not value:
        return ""
    covar_keyname = "name"
    if hasattr(field, "covar_keyname"):
        covar_keyname = field.covar_keyname

    for covariate in value:
        if covariate["name"] != field.alias:
            continue
        values = covariate["value"]
        if not isinstance(values, list):
            return values
        sorted(values, key=lambda x: (x["area"]), reverse=True)
        return values[0][covar_keyname] if values else ""

    return ""
