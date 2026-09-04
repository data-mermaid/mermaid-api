"""C4: keys die when the relationship that justified them dies.

An API key acts as its profile, so most of this takes care of itself: losing a
project membership loses the key's access to that project on the next request,
because the key has no scope of its own to fall out of step with the
memberships, and a deleted profile takes its keys with it through the FK
cascade.

What is left is the case the ORM does not cover: a profile that stops being a
valid caller while its row stays behind.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from ..models import APIKey, Profile

PROFILE_DEACTIVATED = "profile_deactivated"


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
