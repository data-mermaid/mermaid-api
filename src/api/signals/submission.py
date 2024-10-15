import django.dispatch

# After a Collect Record has been converted to a Sample Unit.
post_submit = django.dispatch.Signal()

# After a Sample Unit has been converted back to a Collect Record.
post_edit = django.dispatch.Signal()
