import logging

import django_filters
from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import JSONField
from django.db.models.expressions import RawSQL
from psycopg.errors import UniqueViolation
from rest_condition import Or
from rest_framework import exceptions, permissions, serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response

from ..auth_backends import AnonymousJWTAuthentication
from ..exceptions import check_uuid
from ..models import (
    Management,
    Profile,
    Project,
    ProjectProfile,
    Site,
    Tag,
    TransectMethod,
)
from ..notifications import notify_crs_transferred
from ..permissions import (
    ProjectDataAdminPermission,
    ProjectDataPermission,
    UnauthenticatedReadOnlyPermission,
    get_project,
    get_project_pk,
)
from ..reports.fields import ReportField, ReportMethodField
from ..reports.formatters import to_data_policy, to_str, to_yesno
from ..reports.report_serializer import ReportSerializer
from ..utils import get_extent, truthy
from ..utils.project import (
    citation_retrieved_text,
    copy_project_and_resources,
    create_collecting_summary,
    create_submitted_summary,
    default_citation,
    delete_project,
    email_members_of_new_project,
    get_profiles,
    get_sample_unit_field,
    suggested_citation,
)
from ..utils.q import submit_job
from ..utils.replace import replace_collect_record_owner, replace_sampleunit_objs
from .base import (
    BaseAPIFilterSet,
    BaseAPISerializer,
    BaseApiViewSet,
    BaseInFilter,
    TagField,
)
from .management import ManagementSerializer
from .mixins import DynamicFieldsMixin, OrFilterSetMixin
from .project_profile import ProjectProfileSerializer
from .site import SiteSerializer

logger = logging.getLogger(__name__)


class BaseProjectSerializer(DynamicFieldsMixin, BaseAPISerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cached_profiles = {}

    countries = serializers.SerializerMethodField()
    num_sites = serializers.SerializerMethodField()
    num_active_sample_units = serializers.SerializerMethodField()
    num_sample_units = serializers.SerializerMethodField()
    tags = serializers.ListField(source="tags.all", child=TagField(), required=False)
    members = serializers.SerializerMethodField()
    default_citation = serializers.SerializerMethodField()
    suggested_citation = serializers.SerializerMethodField()
    citation_retrieved_text = serializers.SerializerMethodField()
    bbox = serializers.SerializerMethodField()

    class Meta:
        model = Project
        exclude = []
        hidden_fields = ["default_citation", "user_citation", "citation_retrieved_text"]
        additional_fields = ["countries", "num_sites", "bbox"]

    def _get_profiles(self, obj):
        project_id = str(obj.id)
        if project_id not in self._cached_profiles or self._cached_profiles[project_id] is None:
            self._cached_profiles[project_id] = get_profiles(obj)
        return self._cached_profiles[project_id]

    def get_citation_retrieved_text(self, obj):
        return citation_retrieved_text(obj.name)

    def get_default_citation(self, obj):
        profiles = self._get_profiles(obj)
        return default_citation(obj, profiles)

    def get_suggested_citation(self, obj):
        profiles = self._get_profiles(obj)
        return f"{suggested_citation(obj, profiles)} {citation_retrieved_text(obj.name)}"

    def get_countries(self, obj):
        sites = obj.sites.all()
        return sorted(list(set([s.country.name for s in sites if s.country is not None])))

    def get_num_sites(self, obj):
        sites = obj.sites.all()
        return sites.count()

    def get_members(self, obj):
        profiles = self._get_profiles(obj)
        return [pp.profile_id for pp in profiles]

    def get_num_active_sample_units(self, obj):
        return obj.collect_records.count()

    def get_num_sample_units(self, obj):
        sample_unit_methods = TransectMethod.__subclasses__()
        num_sample_units = 0
        for sample_unit_method in sample_unit_methods:
            sample_unit_name = get_sample_unit_field(sample_unit_method)
            qry_filter = {f"{sample_unit_name}__sample_event__site__project_id": obj}
            queryset = sample_unit_method.objects.select_related(
                f"{sample_unit_name}",
                f"{sample_unit_name}__sample_event",
                f"{sample_unit_name}__sample_event__site",
            )
            num_sample_units += queryset.filter(**qry_filter).count()

        return num_sample_units

    def get_bbox(self, obj):
        extent = getattr(obj, "extent", None)
        return get_extent(extent)


class ProjectSerializer(BaseProjectSerializer):
    @transaction.atomic()
    def create(self, validated_data):
        p = super().create(validated_data)
        request = self.context.get("request")
        pp = ProjectProfile(project=p, profile=request.user.profile, role=ProjectProfile.ADMIN)
        pp.save()
        return p

    def update(self, instance, validated_data):
        request = self.context.get("request")
        profile = request.user.profile

        tags_data = []
        if "tags" in validated_data:
            tags_data = validated_data["tags"].get("all") or []
            del validated_data["tags"]
        instance = super().update(instance, validated_data)

        # Pre-create any missing tags with created_by/updated_by, ensuring post-save signal triggers email
        tag_names = [t.name for t in tags_data]
        existing_tags = Tag.objects.filter(name__in=tag_names)
        existing_names = set(t.name for t in existing_tags)
        for name in tag_names:
            if name not in existing_names:
                tag = Tag(name=name, created_by=profile, updated_by=profile)
                tag.save()

        # all tags now exist and have metadata
        instance.tags.set(tag_names)
        return instance


class ProjectCSVSerializer(ReportSerializer, BaseProjectSerializer):
    fields = [
        ReportField("name", "Project Name"),
        ReportMethodField("get_num_sites", "Number of Sites"),
        ReportMethodField("get_num_sample_units", "Number of Sample Units"),
        ReportMethodField("get_tags", "Organizations"),
        ReportField("data_policy_beltfish", "Beltfish Data Policy", to_data_policy),
        ReportField("data_policy_benthiclit", "Benthic LIT Data Policy", to_data_policy),
        ReportField("data_policy_benthicpit", "Benthic PIT Data Policy", to_data_policy),
        ReportField(
            "data_policy_habitatcomplexity", "Habitat Complexity Data Policy", to_data_policy
        ),
        ReportField("data_policy_bleachingqc", "Bleaching QC Data Policy", to_data_policy),
        ReportField("data_policy_benthicpqt", "Benthic PQT Data Policy", to_data_policy),
        ReportField("includes_gfcr", "Includes GFCR", to_yesno),
        ReportField("notes", "Notes"),
        ReportMethodField("get_project_admins", "Project Admins"),
        ReportMethodField("get_contact_link", "Contact link"),
        ReportField("id", "Project Id", to_str),
    ]

    def get_tags(self, obj):
        tags = obj.tags.all().values_list("name", flat=True)
        if tags:
            return f'{", ".join(tags)}'
        return ""

    def get_contact_link(self, obj):
        return f"{settings.DEFAULT_DOMAIN_MARKETING}/contact-project?project_id={obj.id}"

    def get_project_admins(self, obj):
        admins = obj.profiles.filter(role=ProjectProfile.ADMIN).values_list(
            "profile__email", flat=True
        )
        return ", ".join(admins)


class ProjectFilterSet(BaseAPIFilterSet, OrFilterSetMixin):
    name = BaseInFilter(method="char_lookup")
    tags = django_filters.CharFilter(distinct=True, method="filter_tags")
    country = BaseInFilter(method="site_country")

    class Meta:
        model = Project
        exclude = []
        filter_overrides = {
            JSONField: {
                "filter_class": django_filters.CharFilter,
                "extra": lambda f: {
                    "lookup_expr": "icontains",
                },
            }
        }

    def filter_tags(self, queryset, name, value):
        values = [v.strip() for v in value.split(",")]
        return queryset.filter(tags__name__in=values)

    def site_country(self, queryset, name, value):
        return self.char_lookup(queryset, "sites__country__name", value)


class ProjectAuthenticatedUserPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if user.is_authenticated is False:
            return False
        elif request.method in permissions.SAFE_METHODS or request.method == "POST":
            return True
        elif hasattr(view, "action_map") and "put" in view.action_map:
            action = view.action_map["put"]
            if action in ("find_and_replace_sites", "find_and_replace_managements"):
                pk = get_project_pk(request, view)
                project = get_project(pk)
                pp = ProjectProfile.objects.get_or_none(project=project, profile=user.profile)
                if pp is None:
                    return False
                return pp.role > ProjectProfile.READONLY

        return False


class ProjectViewSet(BaseApiViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [
        Or(
            UnauthenticatedReadOnlyPermission,
            ProjectAuthenticatedUserPermission,
            ProjectDataAdminPermission,
        )
    ]
    method_authentication_classes = {"GET": [AnonymousJWTAuthentication]}
    filterset_class = ProjectFilterSet
    search_fields = ["$name", "$sites__country__name"]

    def get_queryset(self):
        qs = (
            Project.objects.select_related(
                "created_by",
                "updated_by",
            )
            .prefetch_related(
                "profiles",
                "sites",
                "sites__country",
            )
            .annotate(
                # need to cast to text to avoid box2d equality operator error
                extent=RawSQL(
                    """
                    (
                        SELECT ST_Extent(site.location)::text
                        FROM site
                        WHERE site.project_id = project.id
                    )
                    """,
                    [],
                )
            )
            .order_by("name")
        )
        user = self.request.user
        show_all = "showall" in self.request.query_params

        if show_all is True:
            return qs.all()

        if user is None or user.is_authenticated is False:
            return qs.none()
        else:
            profile = user.profile
            return qs.filter(profiles__profile=profile)

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[ProjectAuthenticatedUserPermission],
    )
    def create_project(self, request):
        has_validation_errors = False
        validation_errors = {}
        data = request.data
        context = {"request": request}
        save_point_id = transaction.savepoint()

        project_data = data.get("project")
        profiles_data = data.get("profiles") or []
        sites_data = data.get("sites") or []
        managements_data = data.get("managements") or []
        tags_data = data.get("tags") or []

        if project_data is None:
            transaction.savepoint_rollback(save_point_id)
            raise exceptions.ParseError("No project data specified")

        # Save Project
        project_data["id"] = None
        project_serializer = ProjectSerializer(data=project_data, context=context)
        if project_serializer.is_valid() is False:
            errors = {"Project": project_serializer.errors}
            raise exceptions.ParseError(errors)

        project = project_serializer.save()

        # Save Project Profiles
        for profile_data in profiles_data:
            data = dict(
                id=None,
                project=project.pk,
                profile=profile_data.get("profile"),
                role=profile_data.get("role"),
            )
            pp_serializer = ProjectProfileSerializer(data=data, context=context)
            if pp_serializer.is_valid() is False:
                validation_errors["Users"] = pp_serializer.errors
                has_validation_errors = True
            else:
                pp_serializer.save()

        # Save Sites
        for site_data in sites_data:
            site_data["predecessor"] = site_data["id"]
            site_data["project"] = project.pk
            site_data["id"] = None
            site_serializer = SiteSerializer(data=site_data, context=context)
            if site_serializer.is_valid() is False:
                validation_errors["Sites"] = site_serializer.errors
                has_validation_errors = True
            else:
                site_serializer.save()

        # Save Managements
        for management_data in managements_data:
            management_data["predecessor"] = management_data["id"]
            management_data["project"] = project.pk
            management_data["id"] = None
            mgmt_serializer = ManagementSerializer(data=management_data, context=context)
            if mgmt_serializer.is_valid() is False:
                validation_errors["Management Regimes"] = mgmt_serializer.errors
                has_validation_errors = True
            else:
                mgmt_serializer.save()

        project.tags.add(*tags_data)

        if has_validation_errors is True:
            transaction.savepoint_rollback(save_point_id)
            raise exceptions.ParseError(validation_errors)

        transaction.savepoint_commit(save_point_id)
        return Response(project_serializer.data)

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[ProjectAuthenticatedUserPermission],
    )
    def copy_project(self, request):
        """
        Payload schema:

        {
            "new_project_name": [string] New project name
            "original_project_id": [string] Project id to copy
            "notify_users": [boolean] Sends email to all members of new project. (defaults: false)
        }

        """

        profile = request.user.profile

        data = request.data
        try:
            new_project_name = data["new_project_name"]
        except KeyError as e:
            raise exceptions.ParseError(detail="'new_project_name' is required") from e

        existing_named_projects = Project.objects.filter(name=new_project_name)
        if existing_named_projects.count() > 0:
            raise exceptions.ValidationError({"new_project_name": "Project name already exists"})

        try:
            original_project_id = data["original_project_id"]
            if original_project_id and str(original_project_id).strip() != "":
                check_uuid(original_project_id)
            original_project = ProjectProfile.objects.get(
                project_id=original_project_id, profile=profile
            ).project
        except KeyError as e:
            raise exceptions.ParseError(detail="'original_project_id' is required") from e
        except ProjectProfile.DoesNotExist as not_exist_err:
            raise exceptions.ParseError(
                detail="Original project does not exist or you are not a member"
            ) from not_exist_err

        notify_users = truthy(data.get("notify_users"))

        try:
            new_project = copy_project_and_resources(
                owner_profile=profile,
                new_project_name=new_project_name,
                original_project=original_project,
            )

            if notify_users:
                email_members_of_new_project(new_project, profile)

            context = {"request": request}
            project_serializer = ProjectSerializer(instance=new_project, context=context)
            return Response(project_serializer.data)
        except Exception as err:
            print(err)
            raise exceptions.APIException(detail=f"[{type(err).__name__}] Copying project") from err

    def _find_and_replace_objs(self, request, pk, obj_cls, field, *args, **kwargs):
        project_id = pk
        qp_find_obj_ids = request.data.get("find")
        qp_replace_obj_id = request.data.get("replace")

        if qp_find_obj_ids is None:
            raise exceptions.ValidationError("'find' is required", code=400)

        if qp_replace_obj_id is None:
            raise exceptions.ValidationError("'replace' is required", code=400)

        profile = request.user.profile
        with transaction.atomic():
            sid = transaction.savepoint()
            try:
                replace_obj = obj_cls.objects.get(id=qp_replace_obj_id)
                find_objs = obj_cls.objects.filter(id__in=qp_find_obj_ids, project__id=project_id)
                results = replace_sampleunit_objs(find_objs, replace_obj, field, profile)
                transaction.savepoint_commit(sid)
            except obj_cls.DoesNotExist:
                msg = "Replace {} {} does not exist".format(field, qp_replace_obj_id)
                logger.error(msg)
                transaction.savepoint_rollback(sid)
                raise exceptions.ValidationError(msg, code=400)
            except Exception as err:
                logger.error(err)
                transaction.savepoint_rollback(sid)
                return Response("Unknown error while replacing {}s".format(field), status=500)

        return Response(results)

    @action(detail=True, methods=["put"])
    def find_and_replace_managements(self, request, pk, *args, **kwargs):
        return self._find_and_replace_objs(request, pk, Management, "management", *args, **kwargs)

    @action(detail=True, methods=["put"])
    def find_and_replace_sites(self, request, pk, *args, **kwargs):
        return self._find_and_replace_objs(request, pk, Site, "site", *args, **kwargs)

    def _get_profile(self, project_id, profile_id):
        try:
            return ProjectProfile.objects.get(project_id=project_id, profile_id=profile_id).profile
        except ProjectProfile.DoesNotExist:
            msg = f"[{profile_id}] Profile does not exist in project"
            logger.error("Profile {} does not exist in project {}".format(profile_id, project_id))
            raise exceptions.ValidationError(msg, code=400)

    @action(detail=True, methods=["put"])
    def transfer_sample_units(self, request, pk, *args, **kwargs):
        try:
            project_id = check_uuid(pk)
            project = Project.objects.get(pk=project_id)
        except (exceptions.ParseError, Project.DoesNotExist):
            raise exceptions.ValidationError("Invalid or nonexistent project", code=400)
        qp_to_profile_id = request.data.get("to_profile")
        qp_from_profile_id = request.data.get("from_profile")

        if qp_to_profile_id is None:
            raise exceptions.ValidationError("'to_profile' is required", code=400)

        if qp_from_profile_id is None:
            raise exceptions.ValidationError("'from_profile' is required", code=400)

        from_profile = self._get_profile(project_id, qp_from_profile_id)
        to_profile = self._get_profile(project_id, qp_to_profile_id)

        profile = request.user.profile
        with transaction.atomic():
            sid = transaction.savepoint()
            try:
                num_transferred = replace_collect_record_owner(
                    project_id, from_profile, to_profile, profile
                )
                transaction.savepoint_commit(sid)
                notify_crs_transferred(project, from_profile, to_profile, profile)
            except Exception as err:
                logger.error(err)
                transaction.savepoint_rollback(sid)
                raise Response("Unknown error while replacing sites", status=500)

        return Response({"num_collect_records_transferred": num_transferred})

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        submit_job(0, True, delete_project, instance.pk)

        return Response(
            data="Project has been flagged for deletion",
            status=status.HTTP_202_ACCEPTED,
        )

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[ProjectDataAdminPermission],
    )
    def add_profile(self, request, pk, *args, **kwargs):
        email = request.data.get("email")
        if email is None:
            raise exceptions.ValidationError(detail={"email": "Email is required"})

        email = email.lower()

        try:
            role = int(request.data.get("role"))
        except (TypeError, ValueError):
            role = ProjectProfile.COLLECTOR

        admin_profile = request.user.profile

        profile, _ = Profile.objects.get_or_create(email=email)

        try:
            project_profile, created = ProjectProfile.objects.get_or_create(
                project_id=pk,
                profile=profile,
                role=role,
                created_by=admin_profile,
                updated_by=admin_profile,
            )
            if not created:
                raise exceptions.ValidationError(
                    detail={"email": "Profile has already been added to project"}
                )
        except IntegrityError as ie:
            if isinstance(ie.__cause__, UniqueViolation):
                raise exceptions.ValidationError(
                    detail={"email": "Profile has already been added to project"}
                )
            raise

        return Response(ProjectProfileSerializer(instance=project_profile).data)

    @action(
        detail=True,
        methods=["get"],
        permission_classes=[ProjectDataPermission],
    )
    def summary(self, request, pk, *args, **kwargs):
        project = Project.objects.prefetch_related("sites", "profiles", "collect_records").get(
            id=pk
        )
        summary = {
            "name": project.name,
            "site_collecting_summary": {},
            "site_submitted_summary": {},
        }
        protocols = []

        collecting_protocols, site_collecting_summary = create_collecting_summary(project)
        summary["site_collecting_summary"] = site_collecting_summary
        protocols.extend(collecting_protocols)

        submitted_protocols, site_submitted_summary = create_submitted_summary(project)
        summary["site_submitted_summary"] = site_submitted_summary
        protocols.extend(submitted_protocols)

        summary["protocols"] = sorted(set(protocols))
        return Response(summary)
