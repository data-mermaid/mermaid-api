import csv

from django.http import HttpResponse
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import SAFE_METHODS

from ..ingest.utils import get_su_serializer
from ..permissions import UnauthenticatedReadOnlyPermission


@api_view(SAFE_METHODS)
@authentication_classes([])
@permission_classes((UnauthenticatedReadOnlyPermission,))
def ingest_schema_csv(request, sample_unit):
    serializer = get_su_serializer(sample_unit)
    schema_labels = serializer().get_schema_labels()

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{sample_unit}_template.csv"'
    writer = csv.writer(response)
    writer.writerow(schema_labels)
    return response
