from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from api.models import Site, Tag, UUIDTaggedItem


def test_projecttags_lists_project_and_unused_tags(db, api_client_public, project1, site1):
    project1.tags.add(Tag.objects.create(name="on project"))
    Tag.objects.create(name="unused")
    UUIDTaggedItem.objects.create(
        tag=Tag.objects.create(name="on site only"),
        content_type=ContentType.objects.get_for_model(Site),
        object_id=site1.pk,
    )

    response = api_client_public.get(reverse("projecttag-list"))

    assert response.status_code == 200
    names = {tag["name"] for tag in response.json()["results"]}
    assert {"on project", "unused"} <= names
    assert "on site only" not in names
