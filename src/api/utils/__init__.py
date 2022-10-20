import math
import re
import numbers
import subprocess
import uuid
from datetime import datetime

from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.db.models.deletion import ProtectedError
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
    for subclass in cls.__subclasses__():
        if subclass._meta.abstract:
            yield from get_subclasses(subclass)
            continue
        if subclass.__subclasses__():
            yield from get_subclasses(subclass)
        
        yield subclass
    

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


def delete_instance_and_related_objects(instance):
    protected_objs = get_protected_related_objects(instance)

    for obj in protected_objs:
        try:
            obj.delete()
        except ProtectedError:
            delete_instance_and_related_objects(obj)

    try:
        instance.delete()
    except ProtectedError:
        delete_instance_and_related_objects(instance)


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


def cast_float(val):
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def cast_int(val):
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def run_subprocess(command, std_input=None, to_file=None):
    proc: subprocess.CompletedProcess = None
    try:
        proc = subprocess.run(
            command,
            input=std_input,
            check=True,
            capture_output=True
        )

    except subprocess.CalledProcessError as e:
        print(e.stderr.decode('UTF-8'))
        raise e
    
    # print things like NOTICEs and WARNINGs
    if proc.stderr:
        print(e.stderr.decode('UTF-8'))

    if to_file is not None:
        with open(to_file, "w") as f:
            f.write("DATA: \n")
            f.write(str(proc.stdout))
            f.write("ERR: \n")
            f.write(str(proc.stderr))


# source: https://stackoverflow.com/a/70310511/15624918
def combine_into(d, combined):
    for k, v in d.items():
        if isinstance(v, dict):
            combine_into(v, combined.setdefault(k, {}))
        else:
            combined[k] = v


def is_uuid(val):
    try:
        uuid.UUID(val)
        return True
    except (ValueError, TypeError) as _:
        return False
