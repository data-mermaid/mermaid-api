from ... import utils
from .base import ERROR, OK, WARN, BaseValidator, validator_result


class DrySubmitValidator(BaseValidator):
    UNSUCCESSFUL_SUBMIT = "unsuccessful_dry_submit"

    def _dry_validation_write(self, collect_record, request):
        http_status, results = utils.write_collect_record(
            collect_record, request, dry_run=True
        )
        if http_status == utils.ERROR_STATUS:
            status = ERROR
        elif http_status == utils.VALIDATION_ERROR_STATUS:
            status = WARN
        else:
            status = OK

        return status, results

    @validator_result
    def __call__(self, collect_record, request, **kwargs):
        status, results = self._dry_validation_write(collect_record, request)
        if status in (
            WARN,
            ERROR,
        ):
            return ERROR, self.UNSUCCESSFUL_SUBMIT, {"dry_submit_results": results}
        return OK
