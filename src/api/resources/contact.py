from drf_recaptcha.fields import ReCaptchaV3Field
from rest_framework import serializers, status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ..models import Project
from ..utils.email import email_mermaid_admins, email_project_admins


class ContactSerializer(serializers.Serializer):
    name = serializers.CharField()
    email = serializers.EmailField()
    subject = serializers.CharField()
    message = serializers.CharField()


class ContactMERMAIDSerializer(ContactSerializer):
    recaptcha = ReCaptchaV3Field(action="contact_mermaid")


class ContactProjectAdminsSerializer(ContactSerializer):
    recaptcha = ReCaptchaV3Field(action="contact_project_admins")
    project = serializers.UUIDField()


def _process_contact_request(serializer, email_function):
    serializer.is_valid(raise_exception=True)
    project_id = serializer.validated_data.get("project")
    project = None
    if project_id:
        try:
            project = Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return Response(
                f"project {project_id} does not exist",
                status=status.HTTP_400_BAD_REQUEST,
            )

    kwargs = {
        "name": serializer.validated_data.get("name"),
        "from_email": serializer.validated_data.get("email"),
        "subject": serializer.validated_data.get("subject"),
        "message": serializer.validated_data.get("message"),
        "project": project,
    }
    email_function(**kwargs)

    return Response(status=status.HTTP_200_OK)


@api_view(["POST"])
@authentication_classes([])
@permission_classes((AllowAny,))
def contact_mermaid(request):
    serializer = ContactMERMAIDSerializer(data=request.data, context={"request": request})
    return _process_contact_request(serializer, email_mermaid_admins)


@api_view(["POST"])
@authentication_classes([])
@permission_classes((AllowAny,))
def contact_project_admins(request):
    serializer = ContactProjectAdminsSerializer(data=request.data, context={"request": request})
    return _process_contact_request(serializer, email_project_admins)
