import csv
from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes, authentication_classes

from ..permissions import UnauthenticatedReadOnlyPermission
from ..ingest.utils import get_ingest_schema


@api_view(['GET', 'HEAD', 'OPTIONS'])
@authentication_classes([])
@permission_classes((UnauthenticatedReadOnlyPermission,))
def ingest_schema_csv(request, sample_unit):
    schema = get_ingest_schema(sample_unit)
    csv_column_names = [field["label"] for field in schema]

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{sample_unit}_template.csv"'
    writer = csv.writer(response)
    writer.writerow(csv_column_names)
    return response
