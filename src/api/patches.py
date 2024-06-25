from django.contrib.gis.forms.fields import GeometryField
from django.contrib.gis.gdal import GDALException
from django.core.exceptions import ValidationError

GeometryField._original_to_python = GeometryField.to_python


def patched_geometry_field_to_python(self, value):
    try:
        return self._original_to_python(value)
    except GDALException:
        raise ValidationError(self.error_messages["invalid_geom"], code="invalid_geom")


GeometryField.to_python = patched_geometry_field_to_python
