from django.core.checks import Error, register
from django.core.exceptions import ImproperlyConfigured

from api.utils.apikeys import get_environment_label


@register()
def check_api_key_environment(app_configs, **kwargs):
    """API keys embed an environment label, so ENVIRONMENT must be one we map."""

    try:
        get_environment_label()
    except ImproperlyConfigured as err:
        return [Error(str(err), id="api.E001")]
    return []
