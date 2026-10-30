from ... import utils
from ..statuses import ERROR, OK
from .base import BaseValidator, validator_result


class DrySubmitValidator(BaseValidator):
    UNSUCCESSFUL_SUBMIT = "unsuccessful_dry_submit"

    def _dry_validation_write(self, collect_record, request):
        return utils.write_collect_record(collect_record, request, dry_run=True)

    @validator_result
    def __call__(self, collect_record, request, write_result=None, **kwargs):
        """
        `write_result` is the (status, results) of a write that already ran.
        If given, the dry write is skipped and that result is checked instead.
        """
        http_status, results = write_result or self._dry_validation_write(collect_record, request)
        if http_status in (utils.ERROR_STATUS, utils.VALIDATION_ERROR_STATUS):
            return ERROR, self.UNSUCCESSFUL_SUBMIT, {"dry_submit_results": results}
        return OK
