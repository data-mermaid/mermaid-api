import json
from collections import defaultdict

from .base import ERROR, OK, WARN, BaseValidator, validate_list, validator_result


class RequiredValidator(BaseValidator):
    REQUIRED = "required"

    def __init__(self, path, **kwargs):
        self.path = path
        super().__init__(**kwargs)

    @validator_result
    def __call__(self, collect_record, **kwargs):
        val = self.get_value(collect_record, self.path)
        if val != 0 and (not val or val == ""):
            return ERROR, self.REQUIRED
        return OK


class ListRequiredValidator(BaseValidator):
    REQUIRED = "required"

    def __init__(self, list_path, path, **kwargs):
        self.list_path = list_path
        self.path = path
        self.unique_identifier_label = kwargs.get("unique_identifier_label") or "id"
        self.unique_identifier_key = kwargs.get("unique_identifier_key") or "id"
        super().__init__(**kwargs)

    @validate_list
    def __call__(self, collect_record, **kwargs):
        records = self.get_value(collect_record, self.list_path)
        validator = RequiredValidator(self.path)
        return validator, records


class AllEqualValidator(BaseValidator):
    ALL_EQUAL = "all_equal"

    def __init__(self, path, ignore_keys=None, **kwargs):
        self.path = path
        self.ignore_keys = ignore_keys
        super().__init__(**kwargs)

    def _to_json(self, d):
        self.ignore_keys = self.ignore_keys or []
        return json.dumps({k: v for k, v in d.items() if k not in self.ignore_keys}, sort_keys=True)

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


class DuplicateValidator(BaseValidator):
    DUPLICATE_VALUES = "duplicate_values"

    def __init__(self, list_path, key_paths, **kwargs):
        self.list_path = list_path
        self.key_paths = key_paths
        self.unique_identifier_label = kwargs.get("unique_identifier_label") or "id"
        self.unique_identifier_key = kwargs.get("unique_identifier_key") or "id"
        super().__init__(**kwargs)

    @validator_result
    def __call__(self, collect_record, **kwargs):
        records = self.get_value(collect_record, self.list_path)

        if len(records) < 2:
            return OK

        duplicate_tracker = defaultdict(list)

        for n, record in enumerate(records):
            vals = [str(self.get_value(record, key_path) or "") for key_path in self.key_paths]
            uid = record.get(self.unique_identifier_key)

            duplicate_tracker[":::".join(vals)].append({"id": uid, "index": n})

        duplicates = [r for r in duplicate_tracker.values() if len(r) > 1]
        if not duplicates:
            return OK

        return ERROR, self.DUPLICATE_VALUES, {"duplicates": duplicates}


class PositiveIntegerValidator(BaseValidator):
    NOT_POSITIVE_INTEGER = "not_positive_integer"

    def __init__(self, key_path, **kwargs):
        self.key_path = key_path
        super().__init__(**kwargs)

    @validator_result
    def __call__(self, collect_record, **kwargs):
        val = self.get_value(collect_record, self.key_path)

        if isinstance(val, int) is False or val < 0:
            return ERROR, self.NOT_POSITIVE_INTEGER

        return OK


class ListPositiveIntegerValidator(BaseValidator):
    def __init__(self, list_path, key_path, **kwargs):
        self.list_path = list_path
        self.key_path = key_path
        self.unique_identifier_label = kwargs.get("unique_identifier_label")
        self.unique_identifier_key = kwargs.get("unique_identifier_key")

        super().__init__(**kwargs)

    @validate_list
    def __call__(self, collect_record, **kwargs):
        records = self.get_value(collect_record, self.list_path)
        validator = PositiveIntegerValidator(self.key_path)
        return validator, records
