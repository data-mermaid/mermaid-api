
from django import dispatch
from django.db.models.signals import post_save, pre_delete
from django.contrib.contenttypes.models import ContentType

from ..models import Project, EditedProject
from ..utils.related import get_related_project

IGNORED_MODELS = [
    "editedproject",
    "summarysampleeventmodel",
    "summarysitemodel",
]


def get_all_project_ids():
    qs = Project.objects.filter(status__in=[Project.OPEN, Project.LOCKED])
    return [p.pk for p in qs]


def update_project_changes(instance, *args, **kwargs):
    project = get_related_project(instance)
    project_ids = [project.pk] if project else get_all_project_ids()

    existing_projects = EditedProject.objects.filter(project_pk__in=project_ids).values_list("project_pk", flat=True)
    project_ids = list(set(project_ids).difference(set(existing_projects)))
    if project_ids:
        EditedProject.objects.bulk_create([
            EditedProject(project_pk=pid) for pid in project_ids]
        )


for ct in ContentType.objects.filter(app_label="api"):
    if ct.model in IGNORED_MODELS:
        continue

    model_class = ct.model_class()

    if model_class is None:
        continue

    signal_args = {
        "receiver": update_project_changes,
        "sender": model_class
    }

    post_save.connect(dispatch_uid=f"{model_class._meta.object_name}_post_save", **signal_args)
    pre_delete.connect(dispatch_uid=f"{model_class._meta.object_name}_pre_delete", **signal_args)
