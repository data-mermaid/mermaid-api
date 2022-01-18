import re
from dataclasses import dataclass
from typing import Literal, Optional, Tuple, Union

from dotty_dict import dotty

IGNORE: str = "ignore"
ERROR: str = "error"
WARN: str = "warning"
OK: str = "ok"
STATUSES: Tuple[str] = (ERROR, IGNORE, OK, WARN)


@dataclass
class ValidatorResult:
    name: str
    status: Union[None, Literal[OK, WARN, ERROR, IGNORE]] = None
    code: Optional[str] = None
    context: Optional[dict] = None
    validation_id: Optional[str] = None

    def to_dict(self):
        return {
            "name": self.name,
            "status": self.status,
            "code": self.code,
            "context": self.context,
            "validation_id": self.validation_id,
        }

    @classmethod
    def from_dict(cls, o):
        name = o["name"]
        status = o["status"]
        if status not in STATUSES:
            raise ValueError("Not a valid status")
        code = o.get("code")
        context = o.get("context")

        return cls(
            name=name,
            status=status,
            code=code,
            context=context,
        )


def validator_result(func):
    def class_name(cls):
        return cls.name

    def inner1(*args, **kwargs):
        result = func(*args, **kwargs)
        if isinstance(result, str):
            result = [result]

        result_len = len(result)
        status = result[0]
        code = result[1] if result_len > 1 else None
        context = result[2] if result_len > 2 else None
        return ValidatorResult(
            name=class_name(args[0]),
            status=status,
            code=code,
            context=context,
        )

    return inner1


def validate_list(func):
    def class_name(cls):
        return cls.name

    def _validate(instance, validator_instance, record):
        result = validator_instance(record)
        if hasattr(instance, "unique_identifier_key"):
            uid_key = instance.unique_identifier_key or "id"
            label = uid_key
            if hasattr(instance, "unique_identifier_label"):
                label = instance.unique_identifier_label or label

            result.context = {label: record.get(uid_key)}
            result.name = class_name(instance)

        return result

    def inner(instance, *args, **kwargs):
        validator_instance, records = func(instance, *args, **kwargs)
        return [_validate(instance, validator_instance, r) for r in records]

    return inner


class BaseValidator:
    result = None

    def __init__(self, **kwargs):
        self.context = kwargs or {}

    def __call__(self, *args, **kwargs):
        raise NotImplementedError()

    @property
    def name(self):
        cls_name = self.__class__.__name__
        name = re.sub(r"(?<!^)(?=[A-Z])", "_", cls_name).lower()
        name_prefix = self.context.get("name_prefix")
        if name_prefix is not None:
            name = f"{name_prefix}_{name}"

        return name

    @validator_result
    def skip(self, context=None):
        return OK, None, context

    def get_value(self, record, key):
        data = dotty(record)
        try:
            return data[key]
        except KeyError:
            return None
