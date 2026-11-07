from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from api.models import Notification, Profile, ProjectProfile
from api.utils import normalize_email
from api.utils.notification import suppress_all_notifications

HANDLED_RELATIONS = {(ProjectProfile, "profile"), (Notification, "owner")}


class Command(BaseCommand):
    help = """Clean profile emails containing invisible/whitespace characters (e.g. a pasted
    U+2060 WORD JOINER). If a profile with the clean email already exists, move the bad
    profile's project memberships onto it and delete the bad profile; otherwise just clean
    the email in place. Notifications/emails are suppressed."""

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Report, then roll back")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        bad_ids = [
            pk
            for pk, email in Profile.objects.values_list("id", "email").iterator()
            if normalize_email(email) != email
        ]
        if not bad_ids:
            self.stdout.write("No profile emails need cleaning.")
            return

        prefix = "[DRY RUN] " if dry_run else ""
        with transaction.atomic(), suppress_all_notifications():
            for profile in Profile.objects.filter(pk__in=bad_ids).order_by("created_on"):
                for line in self._fix(profile):
                    self.stdout.write(f"{prefix}{line}")
            if dry_run:
                transaction.set_rollback(True)

    def _blocking_relations(self, profile):
        blocking = []
        for rel in Profile._meta.related_objects:
            if (rel.related_model, rel.field.name) in HANDLED_RELATIONS:
                continue
            count = rel.related_model._base_manager.filter(**{rel.field.name: profile}).count()
            if count:
                blocking.append(f"{rel.related_model.__name__}.{rel.field.name}={count}")
        return blocking

    def _fix(self, profile):
        clean = normalize_email(profile.email)
        label = f"{profile.pk} {ascii(profile.email)}"
        twins = list(Profile.objects.filter(email__iexact=clean).exclude(pk=profile.pk))

        if not twins:
            profile.email = clean
            profile.save()
            return [f"{label}: cleaned email in place -> {clean}"]
        if len(twins) > 1:
            return [f"{label}: SKIPPED, multiple profiles match {clean}"]

        blocking = self._blocking_relations(profile)
        if blocking:
            return [f"{label}: SKIPPED, has other references: {', '.join(blocking)}"]

        twin = twins[0]
        bad_pps = list(ProjectProfile.objects.filter(profile=profile).select_related("project"))
        twin_roles = dict(
            ProjectProfile.objects.filter(profile=twin).values_list("project_id", "role")
        )
        conflicts = [
            f"{pp.project.name} (invite role {pp.role}, existing role {twin_roles[pp.project_id]})"
            for pp in bad_pps
            if pp.project_id in twin_roles and twin_roles[pp.project_id] != pp.role
        ]
        if conflicts:
            return [f"{label}: SKIPPED, role conflict: {'; '.join(conflicts)}"]

        expected_roles = {**twin_roles, **{pp.project_id: pp.role for pp in bad_pps}}
        admin_projects = {pp.project_id for pp in bad_pps if pp.role == ProjectProfile.ADMIN}

        lines = [f"{label}: merging into {twin.pk} {twin.email}"]
        for pp in bad_pps:
            existing = ProjectProfile.objects.filter(project=pp.project, profile=twin).first()
            if existing:
                lines.append(
                    f"    {pp.project.name}: already a member (role {existing.role}); "
                    f"dropping duplicate invite (role {pp.role})"
                )
            else:
                ProjectProfile.objects.create(
                    project=pp.project,
                    profile=twin,
                    role=pp.role,
                    created_by=pp.created_by,
                    updated_by=pp.updated_by,
                )
                lines.append(f"    {pp.project.name}: moved membership (role {pp.role})")
            pp.delete()

        num_notifications, _ = Notification.objects.filter(owner=profile).delete()
        profile.delete()
        lines.append(f"    deleted bad profile and {num_notifications} notification(s)")

        # Hard guarantee: any role deviation aborts and rolls back the whole run.
        actual_roles = dict(
            ProjectProfile.objects.filter(profile=twin).values_list("project_id", "role")
        )
        if actual_roles != expected_roles:
            raise CommandError(
                f"{label}: role mismatch after merge, rolled back. "
                f"expected={expected_roles} actual={actual_roles}"
            )
        for project_id in admin_projects:
            if not ProjectProfile.objects.filter(
                project_id=project_id, role=ProjectProfile.ADMIN
            ).exists():
                raise CommandError(f"{label}: project {project_id} left without admin, rolled back")
        return lines
