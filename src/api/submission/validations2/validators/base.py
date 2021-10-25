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
        return ValidatorResult(class_name(args[0]), *result)

    return inner1


class BaseValidator:
    result = None

    def __init__(self, **kwargs):
        self.context = kwargs

    def __call__(self, *args, **kwargs):
        raise NotImplementedError()

    @property
    def name(self):
        cls_name = self.__class__.__name__
        return re.sub(r"(?<!^)(?=[A-Z])", "_", cls_name).lower()

    @validator_result
    def skip(self):
        return OK

    def get_value(self, record, key):
        data = dotty(record)
        try:
            return data[key]
        except KeyError:
            return None
