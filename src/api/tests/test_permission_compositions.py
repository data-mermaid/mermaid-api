"""
Characterization tests for permission_classes compositions that aren't otherwise
exercised by 403/401 assertions elsewhere in the suite, pinning down current
pass/fail behavior across auth states and roles.

Covers:
- BaseAttributeApiViewSet: UnauthenticatedReadOnlyPermission | AttributeAuthenticatedUserPermission
- ProjectProfileViewSet: ProjectDataReadOnlyPermission | ProjectProfileCollectorPermission | ProjectDataAdminPermission
- ProjectViewSet: UnauthenticatedReadOnlyPermission | ProjectAuthenticatedUserPermission | ProjectDataAdminPermission
- sample-unit-method SE view: ProjectDataReadOnlyPermission | ProjectPublicSummaryPermission
"""

import pytest
from django.urls import reverse

from api.models import BenthicAttribute, ProjectProfile
from api.models.base import PROPOSED, SUPERUSER_APPROVED


@pytest.fixture
def readonly_project_profile3(project1, profile3):
    return ProjectProfile.objects.create(
        project=project1, profile=profile3, role=ProjectProfile.READONLY
    )


# -- BaseAttributeApiViewSet: UnauthenticatedReadOnlyPermission | AttributeAuthenticatedUserPermission --


def test_attribute_viewset_get_allowed_unauthenticated(db_setup, api_client_public):
    response = api_client_public.get(reverse("benthicattribute-list"), format="json")
    assert response.status_code == 200


def test_attribute_viewset_post_denied_unauthenticated(db_setup, api_client_public):
    response = api_client_public.post(
        reverse("benthicattribute-list"), {"name": "Nope"}, format="json"
    )
    assert response.status_code == 401


def test_attribute_viewset_post_allowed_authenticated(db_setup, api_client3):
    response = api_client3.post(
        reverse("benthicattribute-list"), {"name": "New Attribute"}, format="json"
    )
    assert response.status_code == 201


@pytest.fixture
def own_proposed_benthic_attribute(db_setup, profile3):
    """A PROPOSED attribute created by profile3 - BaseAttributeApiViewSet.get_queryset
    restricts non-retrieve actions (update/destroy) to SUPERUSER_APPROVED records or ones
    the requesting user created, so only the creator can reach this record's PUT/DELETE
    branch in AttributeAuthenticatedUserPermission."""
    return BenthicAttribute.objects.create(
        name="Own Proposed Attribute", status=PROPOSED, created_by=profile3
    )


@pytest.fixture
def others_proposed_benthic_attribute(db_setup, profile2):
    return BenthicAttribute.objects.create(
        name="Others Proposed Attribute", status=PROPOSED, created_by=profile2
    )


@pytest.fixture
def own_approved_benthic_attribute(db_setup, profile3):
    return BenthicAttribute.objects.create(
        name="Own Approved Attribute", status=SUPERUSER_APPROVED, created_by=profile3
    )


def test_attribute_viewset_put_allowed_for_own_proposed_status(
    db_setup, api_client3, own_proposed_benthic_attribute
):
    url = reverse("benthicattribute-detail", args=[str(own_proposed_benthic_attribute.pk)])
    response = api_client3.put(url, {"name": "Edited"}, format="json")
    assert response.status_code == 200


def test_attribute_viewset_delete_allowed_for_own_proposed_status(
    db_setup, api_client3, own_proposed_benthic_attribute
):
    url = reverse("benthicattribute-detail", args=[str(own_proposed_benthic_attribute.pk)])
    response = api_client3.delete(url, format="json")
    assert response.status_code == 204


def test_attribute_viewset_put_denied_for_others_proposed_status(
    db_setup, api_client3, others_proposed_benthic_attribute
):
    """BaseAttributeApiViewSet.get_queryset excludes another user's PROPOSED attribute
    from the update/destroy queryset, so AttributeAuthenticatedUserPermission's
    qs.get(id=pk) raises ObjectDoesNotExist and permission is denied."""
    url = reverse("benthicattribute-detail", args=[str(others_proposed_benthic_attribute.pk)])
    response = api_client3.put(url, {"name": "Edited"}, format="json")
    assert response.status_code == 403


def test_attribute_viewset_delete_denied_for_others_proposed_status(
    db_setup, api_client3, others_proposed_benthic_attribute
):
    url = reverse("benthicattribute-detail", args=[str(others_proposed_benthic_attribute.pk)])
    response = api_client3.delete(url, format="json")
    assert response.status_code == 403


def test_attribute_viewset_put_denied_for_own_approved_status(
    db_setup, api_client3, own_approved_benthic_attribute
):
    url = reverse("benthicattribute-detail", args=[str(own_approved_benthic_attribute.pk)])
    response = api_client3.put(url, {"name": "Edited"}, format="json")
    assert response.status_code == 403


def test_attribute_viewset_delete_denied_for_own_approved_status(
    db_setup, api_client3, own_approved_benthic_attribute
):
    url = reverse("benthicattribute-detail", args=[str(own_approved_benthic_attribute.pk)])
    response = api_client3.delete(url, format="json")
    assert response.status_code == 403


def test_attribute_viewset_put_denied_for_unauthenticated(
    db_setup, api_client_public, own_proposed_benthic_attribute
):
    url = reverse("benthicattribute-detail", args=[str(own_proposed_benthic_attribute.pk)])
    response = api_client_public.put(url, {"name": "Edited"}, format="json")
    assert response.status_code == 401


# -- ProjectViewSet: UnauthenticatedReadOnlyPermission | ProjectAuthenticatedUserPermission | ProjectDataAdminPermission --


def test_project_list_allowed_unauthenticated(db_setup, api_client_public, project1):
    response = api_client_public.get(reverse("project-list"), format="json")
    assert response.status_code == 200


def test_project_create_allowed_any_authenticated_user(db_setup, api_client3):
    response = api_client3.post(
        reverse("project-list"), {"name": "Brand New Project"}, format="json"
    )
    assert response.status_code == 201


def test_project_create_denied_unauthenticated(db_setup, api_client_public):
    response = api_client_public.post(
        reverse("project-list"), {"name": "Anon Project"}, format="json"
    )
    assert response.status_code == 401


# -- ProjectProfileViewSet: ProjectDataReadOnlyPermission | ProjectProfileCollectorPermission | ProjectDataAdminPermission --


def test_project_profile_list_allowed_for_readonly_member(
    db_setup, api_client3, project1, readonly_project_profile3
):
    url = reverse("project_profile-list", args=[str(project1.pk)])
    response = api_client3.get(url, format="json")
    assert response.status_code == 200


def test_project_profile_delete_denied_for_readonly_member(
    db_setup, api_client3, project1, readonly_project_profile3, project_profile2
):
    url = reverse("project_profile-detail", args=[str(project1.pk), str(project_profile2.pk)])
    response = api_client3.delete(url, format="json")
    assert response.status_code == 403


def test_project_profile_self_delete_allowed_for_collector(
    db_setup, api_client2, project1, project_profile1, project_profile2
):
    """A COLLECTOR can remove their own project_profile record (ProjectProfileCollectorPermission).
    project_profile1 (ADMIN) must also exist so is_last_admin() has an admin to compare against."""
    url = reverse("project_profile-detail", args=[str(project1.pk), str(project_profile2.pk)])
    response = api_client2.delete(url, format="json")
    assert response.status_code == 204


def test_project_profile_list_denied_for_non_member(db_setup, api_client3, project1):
    url = reverse("project_profile-list", args=[str(project1.pk)])
    response = api_client3.get(url, format="json")
    assert response.status_code == 403


# -- sample-unit-method SE view: ProjectDataReadOnlyPermission | ProjectPublicSummaryPermission --


def test_benthicpit_sampleevent_list_allowed_unauthenticated_public_summary_policy(
    db_setup, api_client_public, project1
):
    """project1 uses the default data_policy_benthicpit (PUBLIC_SUMMARY)."""
    url = reverse("benthicpitmethod-sampleevent-list", args=[str(project1.pk)])
    response = api_client_public.get(url, format="json")
    assert response.status_code == 200


def test_benthicpit_sampleevent_list_denied_unauthenticated_private_policy(
    db_setup, api_client_public, project3
):
    """project3 fixture sets data_policy_benthicpit=PRIVATE."""
    url = reverse("benthicpitmethod-sampleevent-list", args=[str(project3.pk)])
    response = api_client_public.get(url, format="json")
    assert response.status_code == 403


def test_benthicpit_sampleevent_list_allowed_for_project_member_regardless_of_policy(
    db_setup, api_client3, project3, project_profile3
):
    """project_profile3 fixture makes profile3 a COLLECTOR on project3 (PRIVATE policy);
    membership alone (ProjectDataReadOnlyPermission) should still grant read access."""
    url = reverse("benthicpitmethod-sampleevent-list", args=[str(project3.pk)])
    response = api_client3.get(url, format="json")
    assert response.status_code == 200
