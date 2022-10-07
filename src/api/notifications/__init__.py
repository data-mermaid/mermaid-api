from collections import defaultdict
from ..models import CollectRecord, Notification
from ..utils.notification import add_notification


def notify_cr_owners_site_mr_deleted(instance, deleted_by_user):
    lookup = f"data__sample_event__{instance._meta.model_name}"
    collect_records = CollectRecord.objects.filter(**{lookup: instance.pk})
    deleted_by = "An unknown user"
    if deleted_by_user:
        deleted_by = deleted_by_user.full_name
    cr_profiles = defaultdict(int)
    for cr in collect_records:
        cr_profiles[cr.profile] += 1

    for profile, cr_count in cr_profiles.items():
        count = f"{cr_count} unsubmitted sample unit"
        if cr_count > 1:
            count = f"{count}s"
        context = {
            "site_mr": instance._meta.verbose_name,
            "site_mr_name": instance.name,
            "project_name": instance.project.name,
            "deleted_by": deleted_by,
            "cr_count": count,
        }
        notify_template = "notifications/site_mr_deleted.txt"

        add_notification(
            f"Site {instance.name} deleted from {instance.project.name}",
            Notification.WARNING,
            notify_template,
            context,
            [profile],
        )
