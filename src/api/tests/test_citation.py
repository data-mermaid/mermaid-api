from django.urls import reverse
from django.utils import timezone

from api.utils import Testing
from api.utils.summary_cache import update_summary_cache

CUSTOM_CITATION_TEXT = "project1 custom citation"


def _call(client, token, url):
    response = client.get(url, HTTP_AUTHORIZATION=f"Bearer {token}")
    return response.json()


def test_project_view_citation(
    client,
    db_setup,
    project1,
    profile1,
    token1,
    benthic_pit_project,
):
    url = reverse("project-detail", kwargs=dict(pk=project1.pk))

    data = _call(client, token1, f"{url}?showall=true")
    date_text = timezone.localdate().strftime("%B %-d, %Y")
    assert project1.user_citation == ""
    assert data["suggested_citation"].startswith(profile1.last_name)
    assert date_text in data["suggested_citation"]

    project1.user_citation = CUSTOM_CITATION_TEXT
    project1.save()
    data = _call(client, token1, f"{url}?showall=true")
    assert data["suggested_citation"].startswith(CUSTOM_CITATION_TEXT)
    assert date_text in data["suggested_citation"]


def test_obsbenthicpit_view_citation(
    client,
    db_setup,
    project1,
    profile1,
    token1,
    benthic_pit_project,
    obs_benthic_pit1_1,
):
    with Testing():
        url = reverse(
            "benthicpitmethod-obs-detail",
            kwargs=dict(project_pk=project1.pk, pk=obs_benthic_pit1_1.pk),
        )

        update_summary_cache(project1.pk, skip_cached_files=True)
        data = _call(client, token1, url)

        date_text = timezone.localdate().strftime("%B %-d, %Y")
        assert project1.user_citation == ""
        assert data["suggested_citation"].startswith(profile1.last_name)
        assert date_text in data["suggested_citation"]

        project1.user_citation = CUSTOM_CITATION_TEXT
        project1.save()
        update_summary_cache(project1.pk, skip_cached_files=True)
        data = _call(client, token1, url)
        assert data["suggested_citation"].startswith(CUSTOM_CITATION_TEXT)
        assert date_text in data["suggested_citation"]


def test_project_se_summary_citation(
    db_setup,
    api_client1,
    project1,
    profile1,
    benthic_pit_project,
    sample_event1,
):
    with Testing():
        url = reverse("projectsummarysampleevents-list")

        update_summary_cache(project1.pk, skip_cached_files=True)
        request = api_client1.get(url, None, format="json")
        response_data = request.json()
        assert response_data["count"] == 1

        date_text = timezone.localdate().strftime("%B %-d, %Y")
        result = response_data["results"][0]
        assert project1.user_citation == ""
        assert result["suggested_citation"].startswith(profile1.last_name)
        assert date_text in result["suggested_citation"]
        se_citation = result["records"][0]["suggested_citation"]
        assert se_citation.startswith(profile1.last_name)
        assert date_text in se_citation

        project1.user_citation = CUSTOM_CITATION_TEXT
        project1.save()
        update_summary_cache(project1.pk, skip_cached_files=True)
        request = api_client1.get(url, None, format="json")
        response_data = request.json()
        result = response_data["results"][0]
        assert result["suggested_citation"].startswith(CUSTOM_CITATION_TEXT)
        assert date_text in result["suggested_citation"]
