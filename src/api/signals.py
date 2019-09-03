import uuid
from django.dispatch import receiver
from django.db.models.signals import post_delete, post_save, pre_save, m2m_changed
from django import urls
from django.conf import settings
from .models import *
from .utils.email import email_project_admins, mermaid_email
from .submission.utils import validate
from .submission.validations import SiteValidation, ManagementValidation


def get_subclasses(cls):
    result = []
    classes_to_inspect = [cls]
    while classes_to_inspect:
        class_to_inspect = classes_to_inspect.pop()
        for subclass in class_to_inspect.__subclasses__():
            if subclass not in result:
                result.append(subclass)
                classes_to_inspect.append(subclass)
    return result


def reverse_onetoone_delete(sender, instance, *args, **kwargs):
    for f in sender._meta.get_fields():
        if f.one_to_one and not f.auto_created:
            # print(sender, instance, f.name, f.is_relation, f.auto_created)
            reverse_instance = getattr(instance, f.name, None)
            if reverse_instance:
                reverse_instance.delete()


def backup_model_record(sender, instance, using, **kwargs):
    try:
        if (instance._meta.app_label != "api" or
                instance._meta.model_name == 'archivedrecord' or
                not isinstance(instance.pk, uuid.UUID)):
            return

        project_pk = None
        if hasattr(instance, "project_lookup"):
            project_lookup = instance.project_lookup.split("__")
            project = operator.attrgetter(".".join(project_lookup))(instance)
            project_pk = project.pk

        data = serializers.serialize("json", [instance])
        record = dict(
            app_label=instance._meta.app_label,
            model=instance._meta.model_name,
            record_pk=instance.pk,
            project_pk=project_pk,
            record=json.loads(data)[0]
        )
        ArchivedRecord.objects.create(**record)
    except Exception as err:
        logger.exception(err)


def set_created_by(sender, instance, **kwargs):
    if instance._meta.app_label != "api":
            return

    if instance.updated_on is None and hasattr(instance, "updated_by") and getattr(instance, "updated_by") is not None:
        instance.created_by = instance.updated_by


# send email if a new attribute/tag/etc. is created (not updated), AND it was created by a user (not via ingestion),
# AND it was not created by an admin
def email_superadmin_on_new(sender, instance, created, **kwargs):
    admin_emails = [e[1] for e in settings.ADMINS] + [settings.SUPERUSER[1]]
    instance_label = sender._meta.verbose_name or 'instance'

    if created is True and instance.updated_by is not None and instance.updated_by.email not in admin_emails:
        html_content = '''
        <p>{from_name} has proposed a new {instance_label} for MERMAID: {attrib_name}</p>
        <p>To respond, please use the admin interface:<br />
        {admin_link}
        </p>
        <p>You can either:
          <ol>
            <li>change status to 'superuser approved' and save</li>
            <li>delete, and select a new {instance_label} to replace all existing uses of the proposed
            {instance_label}</li>
            <li>communicate further with the user below and come back to this admin to choose</li>
          </ol>
        </p>
        <p>The email address of the user who proposed the {instance_label} is:
        <a href="mailto:{from_email}">{from_email}</a></p>
        '''
        from_name = instance.updated_by.full_name
        from_email = instance.updated_by.email
        reverse_str = "admin:{}_{}_change".format(sender._meta.app_label, sender._meta.model_name)
        admin_link = '{}{}'.format(settings.DEFAULT_DOMAIN_API, urls.reverse(reverse_str, args=[instance.pk]))

        mermaid_email(
            subject='New {} proposed for MERMAID by {}'.format(instance_label, from_name),
            heading='MERMAID Collect Proposed New {}'.format(instance_label.title()),
            subheading='MERMAID SuperAdmin Communication',
            body=html_content.format(
                from_name=from_name,
                attrib_name=str(instance),
                admin_link=admin_link,
                from_email=from_email,
                instance_label=instance_label,
            ),
            to=[settings.SUPERUSER[1]],
            # from_email=[instance.updated_by.email]
        )


# Attach post-delete signal on every model with a OneToOneField to delete its reverse relation instance.
# Auto-created OneToOnes from inheritance get deleted automatically.
for c in get_subclasses(BaseModel):
    post_delete.connect(reverse_onetoone_delete, sender=c, dispatch_uid='{}_delete'.format(c._meta.object_name))
    post_delete.connect(backup_model_record, sender=c, dispatch_uid='{}_delete_archive'.format(c._meta.object_name))
    pre_save.connect(set_created_by, sender=c, dispatch_uid='{}_set_created_by'.format(c._meta.object_name))

for c in get_subclasses(BaseAttributeModel):
    post_save.connect(email_superadmin_on_new, sender=c, dispatch_uid='{}_save'.format(c._meta.object_name))
post_save.connect(email_superadmin_on_new, sender=Tag, dispatch_uid='{}_save'.format(Tag._meta.object_name))


def notify_admins_project_change(instance, text_changes):
    subject = u'Changes to {}'.format(instance.name)
    collect_project_url = '{}/#/projects/{}/details'.format(settings.DEFAULT_DOMAIN_COLLECT, instance.pk)
    collect_project_link = '<a href="{}">{}</a>'.format(collect_project_url, collect_project_url)

    updated_by = u''
    email = u''
    if instance.updated_by is not None:
        updated_by = instance.updated_by.full_name
        email = instance.updated_by.email
    editor = u'{} &lt;{}&gt;'.format(updated_by, email)
    body = u"""
    <p>
    Because you are an administrator of this project, we are letting you know that the changes listed below were
    just made by:<br>
    {}<br>
    If these changes were made by a co-administrator, contact that person to discuss any possible revisions.
    If neither you nor a co-administrator made the changes, make sure all project user roles are set
    appropriately, and all project administrators should immediately change passwords by navigating to 'Your
    profile' in the MERMAID menu and then clicking the 'Send Change Password Email' button.
    </p>
    <p>
    To view your project settings, click or point your browser to:<br>
    {}
    </p>
    <h4>Summary of changes:</h4>
    {}
    """.format(editor, collect_project_link, u'\n'.join(text_changes))

    email_project_admins(instance, subject, body)


@receiver(post_save, sender=Project)
def notify_admins_project_instance_change(sender, instance, created, **kwargs):
    if not created:
        old_values = instance._old_values
        new_values = instance._new_values
        diffs = [(k, (v, new_values[k])) for k, v in old_values.items() if v != new_values[k]]
        if diffs:
            text_changes = []
            for diff in diffs:
                field = sender._meta.get_field(diff[0])
                fname = field.verbose_name
                oldval = diff[1][0]
                newval = diff[1][1]
                if field.choices:
                    oldval = dict(field.choices)[diff[1][0]]
                    newval = dict(field.choices)[diff[1][1]]
                text_changes.append(u'<p>Old {}: {}<br>\nNew {}: {}</p>'.format(fname, oldval, fname, newval))

            notify_admins_project_change(instance, text_changes)


@receiver(m2m_changed, sender=Project.tags.through)
def notify_admins_project_tags_change(sender, instance, action, reverse, model, pk_set, **kwargs):
    if action == "post_add" or action == "post_remove":
        text_changes = []
        verb = ""
        if action == "post_add":
            verb = "Added"
        elif action == "post_remove":
            verb = "Removed"

        altered_tags = Tag.objects.filter(pk__in=pk_set)
        if altered_tags.count() > 0:
            for t in altered_tags:
                text_changes.append(u"<p>{} organization: {}</p>".format(verb, t.name))

            notify_admins_project_change(instance, text_changes)


def notify_admins_change(instance, changetype):
    if changetype == 'add':
        subject_snippet = u'added to'
        body_snippet = u'given administrative privileges to'
    elif changetype == 'remove':
        subject_snippet = u'removed from'
        body_snippet = u'removed, as administrator or entirely, from'
    else:
        return

    subject = u'Project administrator {} {}'.format(subject_snippet, instance.project.name)
    user = instance.profile.full_name
    collect_project_url = '{}/#/projects/{}/users'.format(settings.DEFAULT_DOMAIN_COLLECT, instance.project.pk)
    collect_project_link = '<a href="{}">{}</a>'.format(collect_project_url, collect_project_url)

    editor_text = u'</p><p>'
    if instance.updated_by is not None:
        editor = u'{} &lt;{}&gt;'.format(instance.updated_by.full_name, instance.updated_by.email)
        editor_text = u"""
        The user who made the change is:<br>
        {}<br>
        """.format(editor)

    body = u"""
    <p>
    Because you are an administrator of this project, we are letting you know that {} was just {} this project.
    If for any reason this is not intended, visit the link below to revise.{}
    If neither you nor a co-administrator made the changes, make sure all project user roles are set
    appropriately, and all project administrators should immediately change passwords by navigating to 'Your
    profile' in the MERMAID menu and then clicking the 'Send Change Password Email' button.
    </p>
    <p>
    To review your project's user roles, click or point your browser to:<br>
    {}
    </p>
    """.format(user, body_snippet, editor_text, collect_project_link)

    email_project_admins(instance.project, subject, body)


@receiver(post_save, sender=ProjectProfile)
def notify_admins_new_admin(sender, instance, created, **kwargs):
    if instance.role >= ProjectProfile.ADMIN:
        notify_admins_change(instance, 'add')
    else:
        if not created:
            old_role = instance._old_values.get('role')
            if old_role >= ProjectProfile.ADMIN:
                notify_admins_change(instance, 'remove')


@receiver(post_delete, sender=ProjectProfile)
def notify_admins_dropped_admin(sender, instance, **kwargs):
    if instance.role >= ProjectProfile.ADMIN:
        notify_admins_change(instance, 'remove')


@receiver(post_delete, sender=Site)
@receiver(post_save, sender=Site)
def run_site_validation(sender, instance, *args, **kwargs):
    if instance.project is None:
        return

    validate(SiteValidation, Site, {"project_id": instance.project_id})

    if 'created' in kwargs:
        # Need to update cached instance to keep
        # PUT/POST responses up to date.
        site = Site.objects.get(id=instance.id)
        instance.validations = site.validations
        instance.updated_on = site.updated_on


@receiver(post_delete, sender=Management)
@receiver(post_save, sender=Management)
def run_management_validation(sender, instance, *args, **kwargs):
    if instance.project is None:
        return

    validate(ManagementValidation, Management, {"project_id": instance.project_id})

    if 'created' in kwargs:
        # Need to update cached instance to keep
        # PUT/POST responses up to date.
        mgmt = Management.objects.get(id=instance.id)
        instance.validations = mgmt.validations
        instance.updated_on = mgmt.updated_on


@receiver(post_delete, sender=CollectRecord)
@receiver(post_save, sender=CollectRecord)
def run_cr_management_validation(sender, instance, *args, **kwargs):
    if instance.project is None:
        return

    data = instance.data or {}
    if 'sample_event' in data:
        mrid = data['sample_event'].get('management')
        if mrid is not None:
            validate(ManagementValidation, Management, {"project_id": instance.project_id})
