from pathlib import Path
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny


@api_view(['GET', 'HEAD', 'OPTIONS'])
@authentication_classes([])
@permission_classes((AllowAny,))
def version(request):
    version = ""
    versionfile = Path("/var/projects/webapp/version.txt")
    if versionfile.is_file():
        version = versionfile.read_text().strip()

    return Response(version)
