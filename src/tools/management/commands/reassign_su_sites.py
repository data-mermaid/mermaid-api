from django.core.management.base import BaseCommand
from api.exceptions import check_uuid
from api.models import SampleEvent, Site, TransectMethod


class Command(BaseCommand):
    help = """For a given list of transect method ids, get/create a SE with the passed site name 
    and the other existing SE attributes, and assign that SE to the SUs"""

    def add_arguments(self, parser):
        parser.add_argument("newsite_name")
        parser.add_argument("tm_ids")

    def handle(self, *args, **options):
        newsite_name = options.get("newsite_name")
        tm_ids = [check_uuid(pk) for pk in options.get("tm_ids").split(",")]

        project = None
        tms = TransectMethod.objects.filter(pk__in=tm_ids)
        for tm in tms:
            p = tm.sample_unit.sample_event.site.project
            if project and p != project:
                raise ValueError("Not all SUs belong to the same project")
            else:
                project = p

        newsite = Site.objects.get(project=project, name=newsite_name)

        for tm in tms:
            su = tm.sample_unit
            existing_se = su.sample_event
            new_se, created = SampleEvent.objects.get_or_create(
                site=newsite,
                management=existing_se.management,
                sample_date=existing_se.sample_date,
                notes=existing_se.notes,
            )
            su.sample_event = new_se
            su.save()
