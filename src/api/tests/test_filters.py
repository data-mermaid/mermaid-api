from api.models import Site


def test_safe_search_filter(
    db_setup, api_client1, base_project
):
    response = api_client1.get("/v1/sites/?search=site", format="json")
    response_data = response.json()

    assert response_data["count"] == Site.objects.filter(name__iregex="site").count()

    response = api_client1.get("/v1/sites/?search=(.*17.*|.*33.*|.*01.*|.*\\..*|.*68,.*|.*94.*|.*30.*|.*45.*|.*\\..*|.*62.*)", format="json")
    assert response.status_code == 400
