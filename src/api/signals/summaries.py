import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from ..models import Management, Project, ProjectProfile, Site, TransectMethod
from ..utils.related import get_related_project
from ..utils.summary_cache import add_project_to_queue

__all__ = (
    "update_summaries_on_delete_transect_method",
    "update_summaries",
)

logger = logging.getLogger(__name__)


@receiver(post_delete, sender=TransectMethod)
def update_summaries_on_delete_transect_method(sender, instance, *args, **kwargs):
    project = get_related_project(instance)
    if project is None:
        return

    sample_unit = instance.sample_unit
    sample_unit.delete()
    try:
        add_project_to_queue(project.pk)
    except Exception:
        logger.exception(f"Failed to queue summary update for project {project.pk}")


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

    try:
        add_project_to_queue(project.pk)
    except Exception as e:
        print(f"Failed to queue summary update for project {project.pk}: {e}")
