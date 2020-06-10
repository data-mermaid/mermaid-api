import math
import re
import numbers
from datetime import datetime

from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.db.models.fields.related import OneToOneRel
from django.contrib.admin.utils import NestedObjects
from django.db import router


def is_match(string, match_patterns):
    for match_pattern in match_patterns:
        if re.search(match_pattern, string) is not None:
            return True
    return False


def get_or_create_safeish(model_cls, **kwargs):
    try:
        return model_cls.objects.get(**kwargs), False
    except ObjectDoesNotExist:
        try:
            return model_cls.objects.create(**kwargs), True
        except IntegrityError:
            return get_or_create_safeish(model_cls, **kwargs)


def calc_biomass_density(
    count,
    size,
    transect_len_surveyed,
    transect_width,
    constant_a,
    constant_b,
    constant_c,
):
    if (
        count is None
        or size is None
        or transect_len_surveyed is None
        or transect_width is None
        or constant_a is None
        or constant_b is None
        or constant_c is None
    ):
        return None

    constant_a = float(constant_a)
    constant_b = float(constant_b)
    constant_c = float(constant_c)

    size = float(size)

    # kg
    biomass = count * constant_a * math.pow((size * constant_c), constant_b) / 1000.0

    # m2 to hectares
    area = transect_len_surveyed * transect_width / 10000.0
    if area == 0:
        return None

    return biomass / area  # kg/ha


def get_subclasses(cls):
    result = []
    classes_to_inspect = [cls]
    while classes_to_inspect:
        class_to_inspect = classes_to_inspect.pop()
        for subclass in class_to_inspect.__subclasses__():
            if subclass not in result:
                classes_to_inspect.append(subclass)
                if not subclass._meta.abstract:
                    result.append(subclass)
    return result


def get_related_transect_methods(model):
    related_objects = [
        f for f in model._meta.get_fields() if isinstance(f, OneToOneRel)
    ]

    return [
        getattr(model, ro.related_name)
        for ro in related_objects
        if hasattr(model, ro.name or "")
    ]


def get_protected_related_objects(instance):
    using = router.db_for_write(instance)
    collector = NestedObjects(using=using)
    collector.collect([instance])
    return collector.protected


def get_sample_unit_number(instance):
    self_number = ""
    self_label = ""
    if hasattr(instance, "number"):
        self_number = instance.number or ""
    if hasattr(instance, "label"):
        self_label = instance.label or ""
    if self_number == "":
        self_number = self_label
    elif self_label != "":
        self_number = "{} {}".format(self_number, self_label)

    return self_number


def safe_sum(*args):
    return sum([v for v in args if isinstance(v, numbers.Number)])


def safe_division(numerator, denominator):
    if isinstance(numerator, numbers.Number) and isinstance(
        denominator, numbers.Number
    ):
        return numerator * 1.0 / denominator
    return None


def get_value(dictionary, keys, delimiter="__"):
    if isinstance(keys, str):
        keys = keys.split(delimiter)
    if not keys or dictionary is None:
        return dictionary
    return get_value(dictionary.get(keys[0]), keys[1:])


def set_value(dic, keys, value, delimiter="__"):
    if isinstance(keys, str):
        keys = keys.split(delimiter)

    for key in keys[:-1]:
        dic = dic.setdefault(key, {})
    dic[keys[-1]] = value


def truthy(val):
    return val in ("t", "T", "true", "True", True, 1)


def create_timestamp(ttl=0):
    return datetime.utcnow().timestamp() + ttl


def expired_timestamp(timestamp):
    return create_timestamp() >= timestamp
