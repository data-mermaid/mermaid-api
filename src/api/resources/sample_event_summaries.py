import math

from django.db.models import Q
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.utils.urls import replace_query_param

from api.utils.timer import Timer
from ..models import Project, SummarySampleEventModel
from .summary_sample_event import SummarySampleEventSerializer


def _build_url(request, page_num):
    url = request.build_absolute_uri()
    return replace_query_param(url, "page", page_num)


@api_view(http_method_names=["GET"])
@authentication_classes([])
@permission_classes((AllowAny,))
def vw_project_sample_event_summaries(request):
    """
    Returns a paginated list of all sample events by project.  Test projects are excluded.
    """
    try:
        limit = int(request.query_params.get("limit", 100))
    except ValueError:
        return Response("Invalid limit", status=400)

    try:
        page_num = int(request.query_params.get("page", 1))
    except ValueError:
        return Response("Invalid page", status=400)

    is_secure = request.user.is_authenticated
    if is_secure:
        profile = request.user.profile
    else:
        profile = None

    qs = SummarySampleEventModel.objects.filter(~Q(project_status=Project.TEST))
    unique_project_ids = qs.values_list("project_id", flat=True).distinct()
    count = len(unique_project_ids)

    start_index = (page_num - 1) * limit
    end_index = page_num * limit
    summaries = (
        qs.filter(project_id__in=unique_project_ids[start_index:end_index])
        .privatize(profile=profile)
        .order_by("project_id")
    )

    project_id = None
    results = []
    project_records = []
    for summary in summaries:
        if project_id != summary.project_id:
            project_id = summary.project_id
            if project_records:
                results.append(
                    {
                        "project_id": project_id,
                        "records": SummarySampleEventSerializer(
                            project_records, many=True
                        ).data,
                    }
                )
            project_records = []
        project_records.append(summary)

    if project_records:
        results.append(
            {
                "project_id": project_id,
                "records": SummarySampleEventSerializer(project_records, many=True).data,
            }
        )

    total_pages = math.ceil(count / limit)
    if total_pages > page_num:
        next_page_num = page_num + 1
        next_url = _build_url(request, next_page_num)
    else:
        next_url = None

    if page_num > 1:
        previous_page_num = page_num - 1
        previous_url = _build_url(request, previous_page_num)
    else:
        previous_url = None

    return Response(
        {"count": count, "next": next_url, "previous": previous_url, "results": results}
    )
