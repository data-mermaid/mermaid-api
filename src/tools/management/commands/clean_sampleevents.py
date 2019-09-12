from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import SampleEvent, SampleUnit
from api.utils import get_subclasses
from api.utils.sample_units import delete_orphaned_sample_event


class Command(BaseCommand):
    help = """Find and remove orphan and duplicate sample events.
    Use --dryrun (or -d) option to test first.
    """

    def __init__(self):
        super(Command, self).__init__()
        self.dryrun = False

    def add_arguments(self, parser):
        parser.add_argument("-d", "--dryrun", action="store_true", default=False,
                            help="Run all cleanup queries inside a transaction that is rolled back")

    def handle(self, *args, **options):
        self.dryrun = options.get("dryrun")
        suclasses = get_subclasses(SampleUnit)

        with transaction.atomic():
            sid = transaction.savepoint()

            for se in SampleEvent.objects.all():
                se_pk = se.pk
                orphaned = delete_orphaned_sample_event(se)
                if orphaned:
                    print('Deleted orphaned SE {}'.format(se_pk))
                    continue

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
                ).exclude(pk=se.pk)

                if dups.count() > 0:
                    print('Removing dups for {}'.format(se.pk))
                    for d in dups:
                        try:
                            se2 = SampleEvent.objects.get(pk=se.pk)

                            for suclass in suclasses:
                                sus = suclass.objects.filter(sample_event=d.pk)
                                for su in sus:
                                    su.sample_event = se
                                    su.save()
                                    print('Changed SE from {} to {} for {} {}'.format(d.pk, se.pk, su._meta.verbose_name,
                                                                                      su.pk))

                            print('Deleting SE {}'.format(d.pk))
                            d.delete()

                        except SampleEvent.DoesNotExist:
                            print('{} already deleted'.format(se.pk))

            if self.dryrun:
                transaction.savepoint_rollback(sid)
            else:
                transaction.savepoint_commit(sid)
