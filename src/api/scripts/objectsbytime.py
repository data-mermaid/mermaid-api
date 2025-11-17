import csv
import datetime
from collections import defaultdict

from dateutil.relativedelta import relativedelta
from django.utils import timezone

from api.models import Profile, SampleUnit, Site
from api.utils import get_subclasses

OBJECT = "object"
START_DATE = "start_date"
END_DATE = "end_date"
COUNT = "count"
fieldnames = [OBJECT, START_DATE, END_DATE, COUNT]

bin_size_years = 1
date_format = "%Y-%m-%d"


def count_by_date(model):
    print(f"model: {model._meta.model_name}")
    modelname = model._meta.model_name
    objs = model.objects.order_by("created_on")
    if hasattr(model, "project_lookup"):
        # print(f"{model.project_lookup}")
        proj_filter = {f"{model.project_lookup}__status__gte": 90}
        objs = model.objects.filter(**proj_filter).order_by("created_on")
    first_year = min(obj.created_on for obj in objs).year
    end_year = max(obj.created_on for obj in objs).year + 1
    start_date = timezone.make_aware(datetime.datetime(first_year, 1, 1))
    end_date = timezone.make_aware(datetime.datetime(end_year, 1, 1))
    current_date = start_date
    bin_counter = []

    while current_date < end_date:
        bin_start = current_date
        bin_end = current_date + relativedelta(years=bin_size_years)
        bin_objs = [obj for obj in objs if bin_start <= obj.created_on < bin_end]
        row = {
            OBJECT: modelname,
            START_DATE: bin_start.strftime(date_format),
            END_DATE: (bin_end - relativedelta(days=1)).strftime(date_format),
            COUNT: len(bin_objs),
        }
        bin_counter.append(row)
        current_date = bin_end

    return bin_counter


def run():
    today = timezone.now().date().isoformat()
    filename = f"objects_by_time-{today}.csv"
    count_data = []

    profile_rows = count_by_date(Profile)
    count_data.extend(profile_rows)

    site_rows = count_by_date(Site)
    count_data.extend(site_rows)

    su_totals = defaultdict(lambda: {COUNT: 0})
    for suclass in get_subclasses(SampleUnit):
        su_rows = count_by_date(suclass)
        for row in su_rows:
            su_date = row[START_DATE]
            su_totals[su_date][END_DATE] = row[END_DATE]
            su_totals[su_date][OBJECT] = "sampleunit"
            su_totals[su_date][COUNT] += row[COUNT]
    su_results = [{START_DATE: date, **data} for date, data in su_totals.items()]
    count_data.extend(su_results)

    with open(filename, "w") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(count_data)
