# import pytest
# from django.contrib.auth.models import User
# from unittest.mock import Mock, patch

# from api.models import Project, ProjectProfile
# from api.reports.summary_report import check_su_method_policy_level


# @pytest.fixture
# def mock_user():
#     user = Mock(spec=User)
#     user.profile = Mock()
#     return user


# @pytest.fixture
# def mock_request(mock_user):
#     request = Mock(user=mock_user)
#     request.user = mock_user
#     return request


# @pytest.fixture
# def mock_projects():
#     project1 = Mock(spec=Project)
#     project1.pk = 1
#     project2 = Mock(spec=Project)
#     project2.pk = 2

#     return [project1, project2]


# @pytest.fixture
# def mock_project_profiles(mock_user, mock_projects):
#     profile1 = Mock(spec=ProjectProfile)
#     profile1.profile = mock_user.profile
#     profile1.project = mock_projects[0]

#     profile2 = Mock(spec=ProjectProfile)
#     profile2.profile = mock_user.profile
#     profile2.project = mock_projects[1]

#     return [profile1, profile2]


# @patch("api.reports.summary_report.Project.objects.filter")
# @patch("api.reports.summary_report.ProjectProfile.objects.filter")
# @patch("api.reports.summary_report.Project.get_sample_unit_method_policy")
# def test_check_su_method_policy_level_private(
#     mock_get_sample_unit_method_policy,
#     mock_project_profile_filter,
#     mock_project_filter,
#     mock_request,
#     mock_projects,
#     mock_project_profiles
# ):
#     mock_get_sample_unit_method_policy.return_value = "data_policy"
#     mock_project_filter.return_value = mock_projects
#     mock_project_profiles[0].project.data_policy = Project.PRIVATE
#     mock_project_profiles[1].project.data_policy = Project.PUBLIC
#     mock_project_profile_filter.return_value = mock_project_profiles

#     result = check_su_method_policy_level(mock_request, "protocol", [1, 2])
#     assert result == Project.PRIVATE


# @patch("api.reports.summary_report.Project.objects.filter")
# @patch("api.reports.summary_report.ProjectProfile.objects.filter")
# @patch("api.reports.summary_report.Project.get_sample_unit_method_policy")
# def test_check_su_method_policy_level_public(
#     mock_get_sample_unit_method_policy,
#     mock_project_profile_filter,
#     mock_project_filter,
#     mock_request,
#     mock_projects,
#     mock_project_profiles
# ):
#     mock_get_sample_unit_method_policy.return_value = "data_policy"
#     mock_project_filter.return_value = mock_projects
#     mock_project_profiles[0].project.data_policy = Project.PUBLIC
#     mock_project_profiles[1].project.data_policy = Project.PUBLIC
#     mock_project_profile_filter.return_value = mock_project_profiles

#     result = check_su_method_policy_level(mock_request, "protocol", [1, 2])
#     assert result == Project.PUBLIC


# @patch("api.reports.summary_report.Project.objects.filter")
# @patch("api.reports.summary_report.ProjectProfile.objects.filter")
# @patch("api.reports.summary_report.Project.get_sample_unit_method_policy")
# def test_check_su_method_policy_level_public_summary(
#     mock_get_sample_unit_method_policy,
#     mock_project_profile_filter,
#     mock_project_filter,
#     mock_request,
#     mock_projects,
#     mock_project_profiles
# ):
#     mock_get_sample_unit_method_policy.return_value = "data_policy"
#     mock_project_filter.return_value = mock_projects
#     mock_project_profiles[0].project.data_policy = Project.PUBLIC_SUMMARY
#     mock_project_profiles[1].project.data_policy = Project.PUBLIC
#     mock_project_profile_filter.return_value = mock_project_profiles

#     result = check_su_method_policy_level(mock_request, "protocol", [1, 2])
#     assert result == Project.PUBLIC_SUMMARY
