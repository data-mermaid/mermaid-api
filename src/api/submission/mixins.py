from django.db import transaction
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.response import Response


class ValidateMixin(object):
    validator_class = None
    validator_identifier = "_root_"

    def _run_validation(self, model, serializer_class, validator, record_id, profile):
        result = validator.validate()
        validation_timestamp = timezone.now()
        validations = dict(
            status=result,
            results=validator.logs,
            last_validated=str(validation_timestamp),
        )
        qry = model.objects.filter(pk=record_id)
        qry.update(
            validations=validations, updated_on=validation_timestamp, updated_by=profile
        )
        record = serializer_class(qry.first()).data

        return result, record

    @action(detail=False, methods=["post"])
    def validate(self, request, project_pk):
        output = dict()
        record_ids = request.data.get("ids") or []
        model_class = self.get_queryset().model

        if self.validator_class is None:
            raise NotImplementedError("validator not defined")

        if self.validator_identifier is None:
            raise NotImplementedError("validator_identifier not defined")

        profile = None
        if hasattr(request, "user") and hasattr(request.user, "profile"):
            profile = request.user.profile

        instances = {
            str(s.pk): s
            for s in model_class.objects.filter(project=project_pk, pk__in=record_ids)
        }

        for record_id in record_ids:
            instance = instances.get(record_id)
            validator = self.validator_class(pk=None)
            validator.identifier = self.validator_identifier

            if instance:
                instance_validations = instance.validations or dict()
                prev_validations = instance_validations.get("results")
                validator.previous_validations = prev_validations
                validator.instance = instance

            status, record = self._run_validation(
                model_class, self.get_serializer_class(), validator, record_id, profile
            )
            output[record_id] = dict(status=status, record=record)

        return Response(output)
