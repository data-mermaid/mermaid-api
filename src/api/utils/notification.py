from contextlib import contextmanager
from contextvars import ContextVar

from django.template.loader import render_to_string

from ..models import Notification

_suppress_notifications: ContextVar[bool] = ContextVar("suppress_notifications", default=False)


@contextmanager
def suppress_all_notifications():
    token = _suppress_notifications.set(True)
    try:
        yield
    finally:
        _suppress_notifications.reset(token)


def add_notification(title, status, template, context, profiles):
    if _suppress_notifications.get():
        return

    context = context or {}
    text_content = render_to_string(template, context=context)

    max_title_length = Notification._meta.get_field("title").max_length
    if len(title) > max_title_length:
        title = title[: max_title_length - 3] + "..."

    notifications = [
        Notification(title=title, status=status, description=text_content, owner=profile)
        for profile in profiles
    ]
    Notification.objects.bulk_create(notifications)
