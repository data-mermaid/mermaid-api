import operator
from . import get_subclasses
from ..models import SampleUnit, TransectMethod, SampleEvent


def delete_orphaned_sample_unit(su, deleted_tm=None):
    deleted = False
    tm_count = None
    # have to make sure there aren't other transect methods of *any* type left for this sample unit
    for tmclass in get_subclasses(TransectMethod):
        # Depends on OneToOne relationship, and `related_name` must end in '_method'
        tm = '{}_method'.format(tmclass._meta.model_name)
        if hasattr(su, tm):
            if tm_count is None:
                tm_count = 0
            if not deleted_tm or (deleted_tm and not type(deleted_tm.subclass) == tmclass):
                tm_count += 1

    if tm_count == 0:
        su.delete()
        deleted = True

    return deleted


def delete_orphaned_sample_event(se, deleted_su=None):
    deleted = False
    su_count = 0
    # have to make sure there aren't other SUs of *any* type left for this SE
    for suclass in get_subclasses(SampleUnit):
        sus = '{}_set'.format(suclass._meta.model_name)
        su_set = operator.attrgetter(sus)(se)
        if deleted_su:
            su_count += su_set.exclude(pk=deleted_su.pk).count()
        else:
            su_count += su_set.all().count()

    if su_count == 0:
        se.delete()
        deleted = True

    return deleted


def find_bpfb_same_sample_event():
    for se in SampleEvent.objects.all():
        if se.benthictransect_set.all().count() > 1 and se.fishbelttransect_set.all().count() > 1:
            print(se.pk)
            break
