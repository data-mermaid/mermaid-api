from django.conf import settings
from django.core.management.base import BaseCommand

from api.models import SampleEvent, FishBeltTransect, BenthicTransect


class Command(BaseCommand):
    help = """Find and remove duplicate sample events.
    """

    def __init__(self):
        super(Command, self).__init__()

    def handle(self, *args, **options):
        for se in SampleEvent.objects.all():
            dups = SampleEvent.objects.filter(
                site=se.site_id,
                management=se.management_id,
                sample_date=se.sample_date,
                sample_time=se.sample_time,
                depth=se.depth,
                visibility=se.visibility,
                current=se.current,
                relative_depth=se.relative_depth,
                tide=se.tide,
            ).exclude(pk=se.id)

            if dups.count() > 0:
                print('Removing dups for {}'.format(se.id))
                for d in dups:
                    fbt = FishBeltTransect.objects.filter(sample_event=d.id)
                    try:
                        se2 = SampleEvent.objects.get(pk=se.id)

                        for f in fbt:
                            f.sample_event = se
                            f.save()
                            print('Changed SE from {} to {} for fish belt transect {}'.format(d.id, se.id, f.id))
                        bt = BenthicTransect.objects.filter(sample_event=d.id)
                        for b in bt:
                            b.sample_event = se
                            b.save()
                            print('Changed SE from {} to {} for benthic transect {}'.format(d.id, se.id, b.id))

                        print('Deleting SE {}'.format(d.id))
                        d.delete()

                    except SampleEvent.DoesNotExist:
                        print('{} already deleted'.format(se.id))
