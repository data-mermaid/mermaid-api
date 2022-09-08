from ..models import (
    BeltTransectWidth,
    BenthicAttribute,
    Current,
    FishSizeBin,
    GrowthForm,
    HabitatComplexityScore,
    ReefSlope,
    RelativeDepth,
    Tide,
    Visibility,
)
from ..models.view_models import FishAttributeView


def build_choices(choices, val_key="name"):
    return [(str(c["id"]), str(c[val_key])) for c in choices]


def belt_transect_widths_choices():
    return build_choices(BeltTransectWidth.objects.choices(order_by="name"), "name")


def benthic_attributes_choices():
    return [
        (str(c.id), str(c.name))
        for c in BenthicAttribute.objects.all().order_by("name")
    ]


def current_choices():
    return build_choices(Current.objects.choices(order_by="name"))


def fish_attributes_choices():
    return [
        (str(c.id), str(c.name))
        for c in FishAttributeView.objects.all().order_by("name")
    ]


def fish_size_bins_choices():
    return build_choices(FishSizeBin.objects.choices(order_by="val"), "val")


def growth_form_choices():
    return build_choices(GrowthForm.objects.choices(order_by="name"))


def tide_choices():
    return build_choices(Tide.objects.choices(order_by="name"))


def reef_slopes_choices():
    return build_choices(ReefSlope.objects.choices(order_by="name"))


def relative_depth_choices():
    return build_choices(RelativeDepth.objects.choices(order_by="name"))


def score_choices():
    return build_choices(
        HabitatComplexityScore.objects.choices(order_by="name"), val_key="val"
    )


def visibility_choices():
    return build_choices(Visibility.objects.choices(order_by="val"))
