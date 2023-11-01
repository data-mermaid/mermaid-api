from collections import Counter
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from api.models import Profile, Site, SampleUnit


bin_size_years = 1
models = [Profile, Site]


def count_objects(model, years):
    print(f"model: {model}")
    objs = model.objects.order_by("created_on")
    if hasattr(model, "project_lookup"):
        proj_filter = {f"{model.project_lookup}__status__gte": 90}
        objs = model.objects.filter(**proj_filter).order_by("created_on")
    first_year = min(obj.created_on for obj in objs).year
    end_year = max(obj.created_on for obj in objs).year + 1
    start_date = timezone.datetime(first_year, 1, 1, tzinfo=timezone.utc)
    end_date = timezone.datetime(end_year, 1, 1, tzinfo=timezone.utc)
    current_date = start_date
    bin_counter = Counter()

    while current_date < end_date:
        bin_start = current_date
        bin_end = current_date + relativedelta(years=bin_size_years)
        bin_objs = [obj for obj in objs if bin_start <= obj.created_on < bin_end]
        bin_counter[bin_start] = len(bin_objs)
        current_date = bin_end

    for bin_start, count in bin_counter.items():
        bin_end = bin_start + relativedelta(years=bin_size_years)
        print(f"Bin {bin_start.strftime('%Y-%m-%d')} to {bin_end.strftime('%Y-%m-%d')}: {count} objects")


def run():
    for model in models:
        count_objects(model, bin_size_years)
    # profiles = Profile.objects.order_by("created_on")
    # first_year = min(profile.created_on for profile in profiles).year
    # end_year = max(profile.created_on for profile in profiles).year + 1
    # start_date = timezone.datetime(first_year, 1, 1, tzinfo=timezone.utc)
    # end_date = timezone.datetime(end_year, 1, 1, tzinfo=timezone.utc)
    # current_date = start_date
    # bin_counter = Counter()
    #
    # while current_date < end_date:
    #     bin_start = current_date
    #     bin_end = current_date + relativedelta(years=bin_size_years)
    #     bin_profiles = [profile for profile in profiles if bin_start <= profile.created_on < bin_end]
    #     bin_counter[bin_start] = len(bin_profiles)
    #     current_date = bin_end
    #
    # for bin_start, count in bin_counter.items():
    #     bin_end = bin_start + relativedelta(years=bin_size_years)
    #     print(f"Bin {bin_start.strftime('%Y-%m-%d')} to {bin_end.strftime('%Y-%m-%d')}: {count} objects")
