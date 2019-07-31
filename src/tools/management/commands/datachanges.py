from datetime import date
from django.utils.encoding import force_bytes

from django.core.management.base import BaseCommand, CommandError
from django.contrib.contenttypes.models import ContentType
import dateutil
import pytz


class Command(BaseCommand):
    SKIP_MODELS = ("growthform", "appversion", "application", "archivedrecord", "uuidtaggeditem")

    def add_arguments(self, parser):
        parser.add_argument('date', type=dateutil.parser.isoparse)
        parser.add_argument(
            '--details',
            dest="show_details",
            action="store_true",
            help='Details of changes',
        )
    
    def get_api_model_classes(self):
        qs = ContentType.objects.filter(app_label='api').exclude(model__in=self.SKIP_MODELS)
        return [c.model_class() for c in qs if c.model_class() is not None]
    
    def get_record_details(self, record):
        return dict(
            id=record.pk,
            updated_on=record.updated_on,
            updated_by=record.updated_by or "",
        )
    
    def get_details(self, queryset):
        return [self.get_record_details(rec) for rec in queryset]


    def handle(self, *args, **kwargs):
        start_date = kwargs.get("date").replace(tzinfo=pytz.utc)
        show_details = kwargs.get("show_details") or False

        api_model_classes = self.get_api_model_classes()

        changes = {}
        for amc in api_model_classes:
            model_name = amc.__name__
            qs = amc.objects.filter(updated_on__gte=start_date)
            details = self.get_details(qs)
            if details:
                changes[model_name] = details
        
        if show_details is True:
            for c in sorted(changes):
                for m in changes[c]:
                    s = b"{model},{id},{updated_on},{updated_by}".format(model=c, **m)
                    print(s)
        else:
            for c in sorted(changes):
                print("{}: {}".format(c, len(changes[c])))
