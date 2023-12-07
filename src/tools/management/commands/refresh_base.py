import json
import os

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from api.models import Profile, Region


# Used by other refresh commands, not this one
def get_regions(region):
    region_ip, _ = Region.objects.get_or_create(name="Indo-Pacific")
    region_c, _ = Region.objects.get_or_create(name="Caribbean")
    REGION_BOTH = "*both regions*"

    chosen_regions = []
    if region is None or region == "":
        chosen_regions.append(region_ip)  # default
    elif region == REGION_BOTH:
        chosen_regions = [region_ip, region_c]
    else:
        try:
            r = Region.objects.get(name=region)
            chosen_regions.append(r)
        except Region.DoesNotExist:
            chosen_regions.append(region_ip)  # default
    return chosen_regions


class Command(BaseCommand):
    help = """Insert lookups and basic entities as part of setting up dev environment.
    NOTE: THIS WILL WIPE OUT EXISTING DATA FIRST.
    """

    def __init__(self):
        super(Command, self).__init__()
        self.source = os.path.join(settings.BASE_DIR, "data", "initial", "base_data.json")
        self.data = None
        self.this_user = None
        self.special_cases = [
            "Account",
            "Organization",
        ]

    def _refresh_model(self, model_name):
        model = apps.get_model(app_label="api", model_name=model_name)
        data = self.data[model_name]
        verbose_name = model._meta.verbose_name_plural.title()
        print("Inserting %s %s..." % (len(data), verbose_name))
        model.objects.all().delete()
        for attribs in data:
            attribs["updated_by"] = self.this_user
        model.objects.bulk_create([model(**attribs) for attribs in data])

    def handle(self, *args, **options):
        with open(self.source) as basedata:
            self.data = json.load(basedata)

            UserModel = get_user_model()
            UserModel.objects.all().delete()
            users = (
                ("dsampson", "dustin@sparkgeo.com"),
                ("edarling", "edarling@wcs.org"),
                ("kfisher", "kfisher@wcs.org"),
                ("nolwero", "nasser.olwero@wwfus.org"),
            )

            for name, email in users:
                um = UserModel.objects.create_user(username=name, email=email, password="abcd1234")
                um.is_superuser = True
                um.is_staff = True
                um.save()

            for model_name in self.data.keys():
                if model_name not in self.special_cases:
                    self._refresh_model(model_name)
