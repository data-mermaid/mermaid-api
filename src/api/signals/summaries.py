from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from ..models import Management, Project, ProjectProfile, Site, Tag, TransectMethod
from ..utils.related import get_related_project
from ..utils.summary_cache import add_project_to_queue

__all__ = (
    "update_summaries_on_delete_transect_method",
    "update_summaries",
)


@receiver(post_delete, sender=TransectMethod)
def update_summaries_on_delete_transect_method(sender, instance, *args, **kwargs):
    project = get_related_project(instance)
    if project is None:
        return

    sample_unit = instance.sample_unit
    sample_unit.delete()
    add_project_to_queue(project.pk)


@receiver(post_delete, sender=Management)
@receiver(post_save, sender=Management)
@receiver(post_delete, sender=Site)
@receiver(post_save, sender=Site)
@receiver(post_delete, sender=ProjectProfile)
@receiver(post_save, sender=ProjectProfile)
@receiver(post_delete, sender=Project)
@receiver(post_save, sender=Project)
def update_summaries(sender, instance, *args, **kwargs):
    project = get_related_project(instance)
    if project is None:
        return

    add_project_to_queue(project.pk)


@receiver(post_delete, sender=Tag)
@receiver(post_save, sender=Tag)
def update_summaries_for_tag(sender, instance, *args, **kwargs):
    ps = Project.objects.filter(tags=instance).only("pk")
    for project in ps:
        add_project_to_queue(project.pk)
