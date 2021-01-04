from ..models import Current, RelativeDepth, Tide, Visibility


def build_choices(choices, val_key="name"):
    return [(str(c["id"]), str(c[val_key])) for c in choices]


def visibility_choices():
    return build_choices(Visibility.objects.choices(order_by="val"))


def current_choices():
    return build_choices(Current.objects.choices(order_by="name"))


def relative_depth_choices():
    return build_choices(RelativeDepth.objects.choices(order_by="name"))


def tide_choices():
    return build_choices(Tide.objects.choices(order_by="name"))
