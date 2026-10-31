from contextlib import contextmanager
from contextvars import ContextVar

from django.core.exceptions import ObjectDoesNotExist
from django.db.models.fields.related import ForeignKey

from api import models

_deferred_projects: ContextVar[dict | None] = ContextVar("deferred_projects", default=None)


@contextmanager
def defer_project_updated_on():
    """
    Save each project once on exit in place of once per record, for the
    update_project_updated_on signal (api/signals/revision.py), while saving
    many related records, e.g. the sample event, sample unit, observers and
    observations of a collect record. Nothing is saved if the block raises.
    """
    projects = {}
    token = _deferred_projects.set(projects)
    try:
        yield
    finally:
        _deferred_projects.reset(token)
    for project in projects.values():
        project.save()


def defer_project_save(project):
    """Queue `project` for saving on exit, if inside defer_project_updated_on."""
    projects = _deferred_projects.get()
    if projects is None:
        return False
    projects.setdefault(project.pk, project)
    return True


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


def get_related_project(model, _visited=None):
    if _visited is None:
        _visited = set()

    pk = getattr(model, "pk", None)
    obj_key = (model.__class__, pk) if pk is not None else id(model)
    if obj_key in _visited:
        return None
    _visited.add(obj_key)

    if isinstance(model, models.Project):
        return model

    try:
        proj = model.project
        if isinstance(proj, models.Project):
            return proj
    except ObjectDoesNotExist:
        return None
    except AttributeError:
        pass

    if hasattr(model, "project_lookup"):
        project_lookup = getattr(model, "project_lookup")
        lookups = project_lookup.split("__")
        rel_obj = get_model_value(model, lookups)
        if rel_obj:
            return rel_obj

    for f in model._meta.get_fields():
        if isinstance(f, ForeignKey):
            try:
                rel_obj = getattr(model, f.name)
            except ObjectDoesNotExist:
                continue
            if rel_obj is not None:
                if isinstance(rel_obj, models.Project):
                    return rel_obj
                rel_obj = get_related_project(rel_obj, _visited)
                if rel_obj:
                    return rel_obj
    return None
