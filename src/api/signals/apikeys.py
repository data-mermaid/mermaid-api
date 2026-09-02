"""C4: keys die when the relationship that justified them dies.

An API key carries its profile's role on the projects it is scoped to. Once
the profile is no longer a member of a project, the key must not keep reaching
it, and a key left with no projects at all is a credential with no purpose -
so it is revoked rather than left dangling.
"""

from django.db.models.signals import post_delete, post_save, pre_delete
from django.dispatch import receiver

from ..models import APIKey, Profile, Project, ProjectProfile
from ..utils.apikeys import audit_logger

PROFILE_DEACTIVATED = "profile_deactivated"


@receiver(post_delete, sender=ProjectProfile, dispatch_uid="ProjectProfile_revoke_api_keys")
def drop_project_from_api_keys(sender, instance, **kwargs):
    """Unscope a removed membership's project, revoking keys left with none.

    `post_delete` does not fire for a `QuerySet.delete()` that bypasses the
    ORM collector, so every path that removes a membership has to delete the
    instance: the sync push handler (`resources/sync/push.py`) and
    `ProjectProfileViewSet` both call `instance.delete()`, and a cascade from
    `Project` or `Profile` goes through the collector, which does fire.
    """

    project_id = instance.project_id
    profile_id = instance.profile_id
    if project_id is None or profile_id is None:
        return

    keys = APIKey.objects.filter(profile_id=profile_id, projects=project_id)
    for key in keys:
        key.projects.remove(project_id)
        audit_logger.info(
            "[apikey.unscoped] key_id=%s profile=%s project=%s",
            key.key_id,
            profile_id,
            project_id,
        )
        if not key.projects.exists():
            key.revoke(APIKey.MEMBERSHIP_REMOVED)


@receiver(pre_delete, sender=Project, dispatch_uid="Project_revoke_api_keys")
def drop_deleted_project_from_api_keys(sender, instance, **kwargs):
    """Unscope a project that is being deleted, revoking keys left with none.

    The cascade removes the scope rows on its own, but it does so without
    firing anything, which would leave a key active with an empty scope - it
    would reach no project data, but would still authenticate. This runs on
    `pre_delete`, while the scope rows are still there to be read.
    """

    for key in APIKey.objects.filter(projects=instance.pk):
        key.projects.remove(instance.pk)
        audit_logger.info(
            "[apikey.unscoped] key_id=%s profile=%s project=%s",
            key.key_id,
            key.profile_id,
            instance.pk,
        )
        if not key.projects.exists():
            key.revoke(APIKey.PROJECT_DELETED)


@receiver(post_save, sender=Profile, dispatch_uid="Profile_revoke_api_keys")
def revoke_api_keys_for_deactivated_profile(sender, instance, **kwargs):
    """Revoke a deactivated profile's keys.

    `Profile` has no deactivation flag today - a deleted profile takes its keys
    with it through the FK cascade. This hook is here so that if one is ever
    added, the keys stop working at the same moment the person does, instead of
    outliving the account silently.
    """

    if getattr(instance, "is_active", True):
        return

    for key in APIKey.objects.filter(profile_id=instance.pk, revoked_at__isnull=True):
        key.revoke(PROFILE_DEACTIVATED)
