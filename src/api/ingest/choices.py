from ..models import (
    BeltTransectWidth,
    BenthicAttribute,
    Current,
    FishSizeBin,
    GrowthForm,
    HabitatComplexityScore,
    InvertBeltTransectWidth,
    InvertClassGroupOfInterest,
    InvertFamily,
    InvertGenus,
    InvertOrder,
    InvertSizeBin,
    InvertSpecies,
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
    return [(str(c.id), str(c.name)) for c in BenthicAttribute.objects.all().order_by("name")]


def current_choices():
    return build_choices(Current.objects.choices(order_by="name"))


def fish_attributes_choices():
    return [(str(c.id), str(c.name)) for c in FishAttributeView.objects.all().order_by("name")]


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
    return build_choices(HabitatComplexityScore.objects.choices(order_by="name"), val_key="val")


def visibility_choices():
    return build_choices(Visibility.objects.choices(order_by="val"))


def invert_attributes_choices():
    choices = []
    for obj in InvertClassGroupOfInterest.objects.select_related(
        "invert_class", "group_of_interest"
    ):
        choices.append((str(obj.pk), f"{obj.invert_class.name} ({obj.group_of_interest.name})"))
    for obj in InvertOrder.objects.all():
        choices.append((str(obj.pk), obj.name))
    for obj in InvertFamily.objects.all():
        choices.append((str(obj.pk), obj.name))
    for obj in InvertGenus.objects.all():
        choices.append((str(obj.pk), obj.name))
    for obj in InvertSpecies.objects.select_related("genus"):
        choices.append((str(obj.pk), f"{obj.genus.name} {obj.name}"))
    return sorted(choices, key=lambda x: x[1])


def invert_belt_transect_widths_choices():
    return sorted(
        [
            (str(w.pk), w.name)
            for w in InvertBeltTransectWidth.objects.all().order_by("name")
            if w.name
        ],
        key=lambda x: x[1],
    )


def invert_size_bins_choices():
    return build_choices(InvertSizeBin.objects.choices(order_by="val"), "val")
