import hashlib
from dataclasses import dataclass
from typing import List, Literal, Union

from dotty_dict import dotty

from .validators import ERROR, IGNORE, OK, WARN, BaseValidator, ValidatorResult

RECORD_KEY = "$record"
RECORD_LEVEL = "record"
ROW_LEVEL = "row"
FIELD_LEVEL = "field"
LEVELS = (
    RECORD_LEVEL,
    ROW_LEVEL,
    FIELD_LEVEL,
)
LIST_VALIDATION_TYPE = "list"
VALUE_VALIDATION_TYPE = "value"
VALIDATION_TYPES = (
    LIST_VALIDATION_TYPE,
    VALUE_VALIDATION_TYPE,
)


@dataclass
class Validation:
    validator: BaseValidator
    paths: List[str]
    validation_level: Literal[RECORD_LEVEL, ROW_LEVEL, FIELD_LEVEL] = FIELD_LEVEL
    validation_type: Literal[
        LIST_VALIDATION_TYPE, VALUE_VALIDATION_TYPE
    ] = VALUE_VALIDATION_TYPE
    result: Union[ValidatorResult, List[ValidatorResult], None] = None
    requires_instance: bool = False

    def _get_validation_id(self):
        parts = [
            self.validator.name,
            "+".join(self.paths),
            self.validation_level,
            self.validation_type,
        ]
        key = "::".join(parts)
        md5_val = hashlib.md5(key.encode("utf-8"))
        return str(md5_val.hexdigest())

    def _assign_validation_id(
        self, result: Union[ValidatorResult, List[ValidatorResult]]
    ):
        if isinstance(result, list):
            for r in result:
                r.validation_id = self._get_validation_id()
        else:
            result.validation_id = self._get_validation_id()

    def run(self, *args, **kwargs):
        result = self.validator(*args, **kwargs)
        self._assign_validation_id(result)
        self.result = result

    def _to_validation_result(self, result):
        o = result.to_dict()
        o["fields"] = self.paths
        return o

    def _to_validation_list_result(self, result):
        output = []
        for r in result:
            o = r.to_dict()
            o["fields"] = self.paths
            output.append(o)
        return output

    def to_validation_result(self):
        if isinstance(self.result, ValidatorResult):
            return self._to_validation_result(self.result)
        elif isinstance(self.result, list):
            return self._to_validation_list_result(self.result)
        raise TypeError("Invalid ValidatorResult")


class ValidationRunner:
    VERSION = "2"
    results = None
    status = OK

    def __init__(self, serializer):
        self.serializer = serializer

    def _get_dotty_value(self, data, key):
        try:
            return data.get(key)
        except (TypeError, KeyError):
            return None

    def _check_is_ignored(
        self,
        new_validator_result: dict,
        existing_validator_results: Union[dict, List[dict]],
    ):
        if not existing_validator_results:
            return False

        return any(
            existing_vr["validation_id"] == new_validator_result["validation_id"]
            and existing_vr["status"] == IGNORE
            for existing_vr in existing_validator_results
        )

    def _set_validator_list_result(self, key, result, existing_validation_result):
        for n, res in enumerate(result):
            if len(self.results[key]) == n:
                self.results[key].append([])

            try:
                is_ignored = self._check_is_ignored(
                    self.results[key][n],
                    existing_validation_result[0]
                )
                res["status"] = IGNORE if is_ignored else res["status"]
            except (IndexError, TypeError):
                is_ignored = False

            self.results[key][n].append(res)

    def set_validator_result(self, validation: Validation, existing_validations: dict):
        self.results = self.results or dotty()
        result = validation.to_validation_result()
        validation_level = validation.validation_level

        if validation_level not in LEVELS:
            raise ValueError("Not sure what you are trying to do")

        validation_type = validation.validation_type
        if validation_type not in VALIDATION_TYPES:
            raise ValueError("Not sure what you are trying to do")

        key = RECORD_KEY if validation_level == RECORD_LEVEL else validation.paths[0]

        self.results.setdefault(key, [])
        existing_validation_result = self._get_dotty_value(existing_validations, key)
        if validation_type == LIST_VALIDATION_TYPE:
            self._set_validator_list_result(key, result, existing_validation_result)
        else:
            is_ignored = self._check_is_ignored(result, existing_validation_result)
            if is_ignored:
                result["status"] = IGNORE

            self.results[key].append(result)

    def _check_result_status(self, result):
        if isinstance(result, ValidatorResult):
            return result.status
        elif isinstance(result, list):
            result_statuses = {res.status for res in result}
            if ERROR in result_statuses:
                return ERROR
            elif WARN in result_statuses:
                return WARN
            return OK

        raise TypeError("Invalid ValidatorResult")

    def validate(self, collect_record, validations, request):
        overall_status = []
        collect_record_dict = self.serializer(instance=collect_record).data
        existing_validations = (
            self._get_dotty_value(dotty(collect_record_dict), "validations.results")
            or dotty()
        )
        for validation in validations:
            if validation.requires_instance is True:
                validation.run(collect_record, request=request)
            else:
                validation.run(collect_record_dict, request=request)
            overall_status.append(self._check_result_status(validation.result))
            self.set_validator_result(validation, existing_validations)

        status = OK
        if ERROR in overall_status:
            status = ERROR
        elif WARN in overall_status:
            status = WARN

        self.status = status
        return status

    def to_dict(self):
        assert (
            self.results is not None
        ), "Cannot call to_dict because nothing has been validated."

        return {
            "version": self.VERSION,
            "status": self.status,
            "results": self.results.to_dict(),
        }
