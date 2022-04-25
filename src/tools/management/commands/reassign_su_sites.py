from django.apps import apps
from django.core.management.base import BaseCommand
from api.exceptions import check_uuid
from api.models import PROTOCOL_MAP


def get_transectmethod(protocol):
    tmtype = ""
    if protocol == "benthiclit":
        tmtype = "benthiclit"
    if protocol == "benthicpit":
        tmtype = "benthicpit"
    if protocol == "fishbelt":
        tmtype = "beltfish"
    if protocol == "bleachingqc":
        tmtype = "bleachingquadratcollection"
    if protocol == "benthicpqt":
        tmtype = "benthicphotoquadrattransect"

    return apps.get_model(app_label="api", model_name=tmtype)


class Command(BaseCommand):
    help = """For a given list of transect method ids, get/create a SE with the passed site name 
    and the other existing SE attributes, and assign that SE to the SUs"""
    protocol_choices = list(PROTOCOL_MAP)

    def add_arguments(self, parser):
        parser.add_argument("newsite_name")
        parser.add_argument("tmtype", choices=self.protocol_choices)
        parser.add_argument("tm_ids")

    def handle(self, *args, **options):
        newsite_name = options.get("newsite_name")
        tmtype = options.get("tmtype")
        tm_ids = [check_uuid(pk) for pk in options.get("tm_ids").split(",")]
        # Could do if PROTOCOL_MAP keys were always model names
        # TMModel = apps.get_model(app_label="api", model_name=tmtype)
        TMModel = get_transectmethod(tmtype)
        Site = apps.get_model(app_label="api", model_name="Site")
        SampleEvent = apps.get_model(app_label="api", model_name="SampleEvent")

        project = None
        tms = TMModel.objects.filter(pk__in=tm_ids)
        for tm in tms:
            p = tm.transect.sample_event.site.project
            if project and p != project:
                raise ValueError("Not all SUs belong to the same project")
            else:
                project = p

        newsite = Site.objects.get(project=project, name=newsite_name)

        for tm in tms:
            su = tm.transect
            existing_se = su.sample_event
            new_se, created = SampleEvent.objects.get_or_create(
                site=newsite,
                management=existing_se.management,
                sample_date=existing_se.sample_date,
                notes=existing_se.notes,
            )
            su.sample_event = new_se
            su.save()
