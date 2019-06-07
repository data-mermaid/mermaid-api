from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny


@api_view(['GET', 'HEAD', 'OPTIONS'])
@authentication_classes([])
@permission_classes((AllowAny,))
def health(request):
    return Response("ok")
