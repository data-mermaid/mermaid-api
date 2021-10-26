import json

from .base import ERROR, OK, WARN, BaseValidator, validator_result


class RequiredValidator(BaseValidator):
    REQUIRED = "required"

    def __init__(self, path):
        self.path = path

    @validator_result
    def __call__(self, collect_record, **kwargs):
        val = self.get_value(collect_record, self.path)
        if val != 0 and not val:
            return ERROR, self.REQUIRED
        return OK


class AllEqualValidator(BaseValidator):
    ALL_EQUAL = "all_equal"

    def __init__(self, path):
        self.path = path

    def _to_json(self, d):
        return json.dumps(d, sort_keys=True)

    @validator_result
    def __call__(self, collect_record, **kwargs):
        values = self.get_value(collect_record, self.path)

        if len(values) < 2:
            return OK

        items = [self._to_json(v) for v in values]
        check_item = items.pop()

        for item in items:
            if item != check_item:
                return OK

        return WARN, self.ALL_EQUAL
