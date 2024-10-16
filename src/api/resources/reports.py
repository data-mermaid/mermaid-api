from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import PROTOCOL_MAP, Project
from ..utils.reports import (
    REPORT_TYPES,
    SAMPLE_UNIT_METHOD_REPORT_TYPE,
    create_sample_unit_method_summary_report_background,
)


class BaseMultiProjectReportSerializer(serializers.Serializer):
    report_type = serializers.ChoiceField(choices=REPORT_TYPES)
    project_ids = serializers.ListField(
        child=serializers.UUIDField(),
    )

    def validate_project_ids(self, value):
        if len(value) < 1:
            raise ValidationError("At least 2 projects are required")

        projects = {str(p.pk): None for p in Project.objects.filter(id__in=value)}
        for project_id in value:
            if project_id not in projects:
                raise ValidationError(f"[{project_id}] Project not found")
        return value


class SampleUnitMethodReportSerializer(BaseMultiProjectReportSerializer):
    protocol = serializers.ChoiceField(choices=[(k, v) for k, v in PROTOCOL_MAP.items()])


class MultiProjectReportView(APIView):
    def get_serializer(self, *args, **kwargs):
        report_type = kwargs.get("data", {}).get("report_type")
        if report_type == SAMPLE_UNIT_METHOD_REPORT_TYPE:
            serializer_class = SampleUnitMethodReportSerializer
        else:
            raise ValidationError(detail="Unknown report type")

        kwargs.setdefault("context", self.get_renderer_context())
        return serializer_class(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        mp_serializer = self.get_serializer(data=request.data)
        mp_serializer.is_valid(raise_exception=True)
        report_type = mp_serializer.validated_data.pop("report_type")

        if report_type == SAMPLE_UNIT_METHOD_REPORT_TYPE:
            project_ids = mp_serializer.validated_data["project_ids"]
            protocol = mp_serializer.validated_data["protocol"]

            create_sample_unit_method_summary_report_background(
                project_ids=project_ids,
                protocol=protocol,
                request=request,
                send_email=True,
            )
        else:
            raise ValidationError(detail=f"{report_type}: Unknown report type")

        return Response({report_type: "ok"})
