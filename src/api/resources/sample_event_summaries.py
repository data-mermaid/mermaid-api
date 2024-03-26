import math

from django.db.models import Q
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.utils.urls import replace_query_param

from ..models import Project, SummarySampleEventModel
from ..utils.castutils import iso8601_to_datetime
from .summary_sample_event import SummarySampleEventSerializer


def _build_url(request, page_num):
    url = request.build_absolute_uri()
    return replace_query_param(url, "page", page_num)


def _get_summaries(profile, page_num, limit, last_created_on=None):
    qs = SummarySampleEventModel.objects.filter(~Q(project_status=Project.TEST))
    if last_created_on:
        count_qs = qs.filter(created_on__gt=last_created_on)
    else:
        count_qs = qs

    unique_project_ids = count_qs.values_list("project_id", flat=True).distinct()
    count = len(unique_project_ids)

    start_index = (page_num - 1) * limit
    end_index = page_num * limit
    return count, qs.filter(project_id__in=unique_project_ids[start_index:end_index]) \
        .privatize(profile=profile) \
        .order_by("project_id")
    

def _group_by_project_id(qs):
    project_id = None
    project_records = []
    for summary in qs:
        if project_id != summary.project_id:
            project_id = summary.project_id
            if project_records:
                yield {
                    "project_id": project_id,
                    "records": SummarySampleEventSerializer(
                        project_records, many=True
                    ).data,
                }
            project_records = []
        project_records.append(summary)

    if project_records:
        yield {
            "project_id": project_id,
            "records": SummarySampleEventSerializer(project_records, many=True).data,
        }


@api_view(http_method_names=["GET"])
@authentication_classes([])
@permission_classes((AllowAny,))
def vw_project_sample_event_summaries(request):
    """
    Returns a paginated list of all sample events by project.  Test projects are excluded.

    Example Response:
    {
        "count": 79,
        "next": null,
        "previous": "http://localhost:8080/v1/project_sample_events/?limit=25&page=3",
        "results": [
            {project_id: 1, records: [{...}, {...}, ...]},
            {project_id: 2, records: [{...}, {...}, ...]},
            ...
        ]
    """
    try:
        limit = int(request.query_params.get("limit", 100))
    except ValueError:
        return Response("Invalid limit", status=400)

    try:
        page_num = int(request.query_params.get("page", 1))
    except ValueError:
        return Response("Invalid page", status=400)

    try:
        last_created_on = iso8601_to_datetime(request.query_params.get("last_created_on"))
    except ValueError:
        last_created_on = None

    is_secure = request.user.is_authenticated
    if is_secure:
        profile = request.user.profile
    else:
        profile = None
    
    count, summaries = _get_summaries(profile, page_num, limit, last_created_on)
    results = _group_by_project_id(summaries)

    total_pages = math.ceil(count / limit)
    if total_pages > 0 and total_pages > page_num:
        next_page_num = page_num + 1
        next_url = _build_url(request, next_page_num)
    else:
        next_url = None

    if total_pages > 0 and page_num > 1:
        previous_page_num = page_num - 1
        previous_url = _build_url(request, previous_page_num)
    else:
        previous_url = None

    return Response(
        {"count": count, "next": next_url, "previous": previous_url, "results": list(results)}
    )
