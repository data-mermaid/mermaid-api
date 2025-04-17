import os

from django.http import FileResponse
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import PROTOCOL_MAP, Project
from ..reports import gfcr
from ..utils import zip_file
from ..utils.reports import (
    GFCR_REPORT_TYPE,
    REPORT_TYPES,
    SAMPLE_UNIT_METHOD_REPORT_TYPE,
    create_sample_unit_method_summary_report,
    create_sample_unit_method_summary_report_background,
)


class BaseMultiProjectReportSerializer(serializers.Serializer):
    report_type = serializers.ChoiceField(choices=REPORT_TYPES)
    project_ids = serializers.ListField(
        child=serializers.UUIDField(),
    )
    background = serializers.BooleanField(default=True)

    def validate_project_ids(self, value):
        if not value:
            raise ValidationError("Project ids are required")

        existing_ids = set(Project.objects.filter(id__in=value).values_list("id", flat=True))
        invalid_ids = [str(pid) for pid in value if pid not in existing_ids]
        if invalid_ids:
            raise ValidationError(f"Projects not found: {', '.join(invalid_ids)}")

        return value


class SampleUnitMethodReportSerializer(BaseMultiProjectReportSerializer):
    protocol = serializers.ChoiceField(choices=[(k, v) for k, v in PROTOCOL_MAP.items()])


class MultiProjectReportView(APIView):
    def get_serializer(self, *args, **kwargs):
        report_type = kwargs.get("data", {}).get("report_type")
        if report_type == SAMPLE_UNIT_METHOD_REPORT_TYPE:
            serializer_class = SampleUnitMethodReportSerializer
        elif report_type == GFCR_REPORT_TYPE:
            serializer_class = BaseMultiProjectReportSerializer
        else:
            raise ValidationError(detail="Unknown report type")

        kwargs.setdefault("context", self.get_renderer_context())
        return serializer_class(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        mp_serializer = self.get_serializer(data=request.data)
        mp_serializer.is_valid(raise_exception=True)
        report_type = mp_serializer.validated_data.pop("report_type")
        background = mp_serializer.validated_data.pop("background")

        output_path = None
        zip_file_path = None

        if report_type == SAMPLE_UNIT_METHOD_REPORT_TYPE:
            project_ids = mp_serializer.validated_data["project_ids"]
            protocol = mp_serializer.validated_data["protocol"]

            if background:
                create_sample_unit_method_summary_report_background(
                    project_ids=project_ids,
                    protocol=protocol,
                    request=request,
                    send_email=True,
                )
            else:
                output_path = create_sample_unit_method_summary_report(
                    project_ids=project_ids,
                    protocol=protocol,
                    request=request,
                    send_email=False,
                )

        elif report_type == GFCR_REPORT_TYPE:
            project_ids = mp_serializer.validated_data["project_ids"]

            if background:
                gfcr.create_report_background(
                    project_ids=project_ids,
                    request=request,
                    send_email=True,
                )
            else:
                output_path = gfcr.create_report(
                    project_ids=project_ids,
                    request=request,
                    send_email=False,
                )
        else:
            raise ValidationError(detail=f"{report_type}: Unknown report type")

        if background:
            return Response({report_type: "ok"})
        else:
            try:
                if not output_path:
                    raise ValidationError("Error creating report")

                zip_file_path = zip_file(output_path, output_path.stem)
                z_file = open(zip_file_path, "rb")
                response = FileResponse(z_file, content_type="application/zip")
                response["Content-Length"] = os.fstat(z_file.fileno()).st_size
                response["Content-Disposition"] = f'attachment; filename="{zip_file_path.stem}.zip"'

                return response
            finally:
                if output_path:
                    output_path.unlink()
                if zip_file_path:
                    zip_file_path.unlink()
