from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET", "HEAD", "OPTIONS"])
@authentication_classes([])
@permission_classes((AllowAny,))
def health(request):
    return Response("ok")
