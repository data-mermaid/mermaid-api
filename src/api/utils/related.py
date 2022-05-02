from django.db.models.fields.related import ForeignKey

from api import models


def get_model_value(model, lookups):
    """Recursively looks up value in model instance.

    :param model: Model Instance
    :type model: Django Model
    :param lookups: List of field names
    :type lookups: list
    :return: Value
    :rtype: Any
    """
    lookup = lookups.pop(0)

    if type(model).__name__ == "RelatedManager":
        related_objects = model.all()
        if related_objects.count() == 0:
            return None
        model = related_objects[0]

    obj = getattr(model, lookup)
    if len(lookups) > 0:
        return get_model_value(obj, lookups)

    return obj


def get_related_project(model):

    if isinstance(model, models.Project):
        return model

    if hasattr(model, "project") and isinstance(model.project, models.Project):
        return model.project

    if hasattr(model, "project_lookup"):
        project_lookup = getattr(model, "project_lookup")
        lookups = project_lookup.split("__")
        rel_obj = get_model_value(model, lookups)
        if rel_obj:
            return rel_obj

    for f in model._meta.get_fields():
        if isinstance(f, ForeignKey):
            rel_obj = getattr(model, f.name)
            if rel_obj is not None:
                if isinstance(rel_obj, models.Project):
                    return rel_obj
                rel_obj = get_related_project(rel_obj)
                if rel_obj:
                    return rel_obj
    return None
