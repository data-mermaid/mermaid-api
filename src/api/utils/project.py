import copy
import logging
import re
import uuid
from collections import defaultdict

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.db.models.fields.related import OneToOneField
from django.utils import timezone
from django.utils.text import slugify

from ..models import (
    BLEACHINGQC_PROTOCOL,
    PROTOCOL_MAP,
    BeltFish,
    BenthicLIT,
    BenthicPhotoQuadratTransect,
    BenthicPIT,
    BenthicTransect,
    BleachingQuadratCollection,
    CollectRecord,
    FishBeltTransect,
    HabitatComplexity,
    Management,
    ObsBeltFish,
    ObsBenthicLIT,
    ObsBenthicPhotoQuadrat,
    ObsBenthicPIT,
    ObsColoniesBleached,
    Observer,
    ObsHabitatComplexity,
    ObsQuadratBenthicPercent,
    Project,
    ProjectProfile,
    QuadratCollection,
    QuadratTransect,
    SampleEvent,
    SampleUnit,
    Site,
    TransectMethod,
)
from ..models.classification import Annotation, Image, Point
from . import delete_instance_and_related_objects, get_value, is_uuid, s3 as s3_utils
from .email import mermaid_email

logger = logging.getLogger(__name__)

UUID_PATTERN = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def _generate_new_image_path(old_path, new_image_id):
    # Replace the UUID in the filename portion with the new image ID
    parts = old_path.rsplit("/", 1)
    if len(parts) == 2:
        directory, filename = parts
        new_filename = UUID_PATTERN.sub(str(new_image_id), filename, count=1)
        return f"{directory}/{new_filename}"
    else:
        return UUID_PATTERN.sub(str(new_image_id), old_path, count=1)


def _copy_s3_image_file(source_path, new_image_id):
    if not source_path:
        return None

    new_path = _generate_new_image_path(source_path, new_image_id)

    try:
        s3_utils.copy_object(
            bucket=settings.IMAGE_PROCESSING_BUCKET,
            source_key=source_path,
            dest_key=new_path,
            aws_access_key_id=settings.IMAGE_BUCKET_AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.IMAGE_BUCKET_AWS_SECRET_ACCESS_KEY,
        )
        return new_path
    except Exception as e:
        logger.warning(f"Failed to copy S3 file {source_path} to {new_path}: {e}")
        return None


def _copy_image(source_image, owner_profile):
    """Copy an Image record and its S3 files, including Points and Annotations."""
    old_image_id = source_image.id
    new_image_id = uuid.uuid4()

    # Copy S3 files (skip annotations_file - will be regenerated)
    new_image_path = _copy_s3_image_file(
        source_image.image.name if source_image.image else None, new_image_id
    )
    new_thumbnail_path = _copy_s3_image_file(
        source_image.thumbnail.name if source_image.thumbnail else None, new_image_id
    )
    new_feature_vector_path = _copy_s3_image_file(
        source_image.feature_vector_file.name if source_image.feature_vector_file else None,
        new_image_id,
    )

    # Use the new image ID as collect_record_id since this is copied submitted data
    # (the original collect record no longer exists for the copied project)
    new_image = Image(
        id=new_image_id,
        collect_record_id=new_image_id,
        name=source_image.name,
        original_image_checksum=source_image.original_image_checksum,
        original_image_name=source_image.original_image_name,
        original_image_width=source_image.original_image_width,
        original_image_height=source_image.original_image_height,
        photo_timestamp=source_image.photo_timestamp,
        location=source_image.location,
        comments=source_image.comments,
        data=copy.deepcopy(source_image.data) if source_image.data else None,
        created_by=owner_profile,
        updated_by=owner_profile,
    )

    if new_image_path:
        new_image.image.name = new_image_path
    if new_thumbnail_path:
        new_image.thumbnail.name = new_thumbnail_path
    if new_feature_vector_path:
        new_image.feature_vector_file.name = new_feature_vector_path

    new_image.save()

    for point in Point.objects.filter(image_id=old_image_id):
        old_point_id = point.id
        point.id = None
        point.image_id = new_image.id
        point.save()

        annotations_to_create = []
        for annotation in Annotation.objects.filter(point_id=old_point_id):
            annotation.id = None
            annotation.point_id = point.id
            annotations_to_create.append(annotation)
        if annotations_to_create:
            Annotation.objects.bulk_create(annotations_to_create)

    new_image.create_annotations_file()

    return new_image


def _get_sample_unit_method_label(sample_unit_method, sample_unit_name):
    number_label = []
    sample_unit = getattr(sample_unit_method, sample_unit_name)
    if hasattr(sample_unit, "number") and sample_unit.number is not None:
        number_label.append(str(sample_unit.number))
    elif sample_unit_method.protocol == BLEACHINGQC_PROTOCOL:
        number_label.append("1")

    if hasattr(sample_unit, "label") and sample_unit.label.strip():
        number_label.append(sample_unit.label)

    return " ".join(number_label)


def get_sample_unit_field(model):
    return next(
        (
            field.name
            for field in model._meta.get_fields()
            if isinstance(field, OneToOneField) and issubclass(field.related_model, SampleUnit)
        ),
        None,
    )


def _create_submitted_sample_unit_method_summary(model_cls, project):
    DEFAULT_UPDATED_BY = "N/A"
    summary = defaultdict(dict)
    protocol = model_cls.protocol
    sample_unit_name = get_sample_unit_field(model_cls)

    if sample_unit_name is None:
        return summary

    qry_filter = {f"{sample_unit_name}__sample_event__site__project_id": project}
    queryset = model_cls.objects.select_related(
        f"{sample_unit_name}",
        f"{sample_unit_name}__sample_event",
        f"{sample_unit_name}__sample_event__site",
        f"{sample_unit_name}__sample_event__management",
        "updated_by",
    ).prefetch_related("observers")
    queryset = queryset.filter(**qry_filter)

    for record in queryset:
        sample_unit = getattr(record, sample_unit_name)
        sample_event = sample_unit.sample_event
        site = sample_event.site
        management = sample_event.management
        site_id = str(site.pk)
        label = _get_sample_unit_method_label(record, sample_unit_name)
        updated_by = DEFAULT_UPDATED_BY
        if sample_unit.updated_by:
            updated_by = sample_unit.updated_by.full_name
        observers = [o.profile_name for o in record.observers.all()]

        if site_id not in summary:
            summary[site_id] = {"site_name": "", "sample_unit_methods": {protocol: []}}

        summary[site_id]["site_name"] = site.name
        summary[site_id]["sample_unit_methods"][protocol].append(
            {
                "id": f"{record.pk}",
                "sample_date": sample_event.sample_date,
                "label": label,
                "management": {
                    "id": management.id,
                    "name": management.name,
                },
                "updated_by": updated_by,
                "observers": observers,
            }
        )

    for site_id in summary:
        s = sorted(
            summary[site_id]["sample_unit_methods"][protocol],
            key=lambda e: f'{e["label"]}:-:{e["sample_date"]}',
        )
        summary[site_id]["sample_unit_methods"][protocol] = s

    return summary


def create_submitted_summary(project):
    summary = {}
    protocols = []
    sample_unit_methods = TransectMethod.__subclasses__()
    for sample_unit_method in sample_unit_methods:
        sample_unit_method_summary = _create_submitted_sample_unit_method_summary(
            sample_unit_method, project
        )

        if not sample_unit_method_summary:
            continue

        protocols.append(sample_unit_method.protocol)
        for site_id in sample_unit_method_summary:
            if site_id not in summary:
                summary[site_id] = sample_unit_method_summary[site_id]
            else:
                summary[site_id]["sample_unit_methods"].update(
                    sample_unit_method_summary[site_id]["sample_unit_methods"]
                )

    return protocols, summary


def _get_collect_record_label(collect_record):
    number_label = []
    sample_unit = collect_record.sample_unit
    number = sample_unit.get("number")
    if collect_record.protocol == BLEACHINGQC_PROTOCOL and number is None:
        number = 1
    label = sample_unit.get("label") or ""
    if number is not None:
        number_label.append(str(number))

    if label.strip():
        number_label.append(label)

    return " ".join(number_label)


def create_collecting_summary(project):
    DEFAULT_SITE_ID = "__null__"
    DEFAULT_MR_ID = "__null__"
    DEFAULT_OBSERVER_NAME = "unnamed observer"
    summary = {}
    collect_records = CollectRecord.objects.select_related("profile").filter(project=project)

    site_ids = []
    mr_ids = []
    for collect_record in collect_records:
        site_id = get_value(collect_record.data or {}, "sample_event.site", ".")
        if is_uuid(site_id) is False:
            continue
        site_ids.append(site_id)
        mr_id = get_value(collect_record.data or {}, "sample_event.management", ".")
        if is_uuid(mr_id) is False:
            continue
        mr_ids.append(mr_id)

    sites = Site.objects.filter(id__in=set(site_ids))
    site_lookup = {str(s.pk): s.name for s in sites}
    managements = Management.objects.filter(id__in=set(mr_ids))
    mr_lookup = {str(mr.pk): mr.name for mr in managements}

    protocols = {}

    for collect_record in collect_records:
        data = collect_record.data or {}
        protocol = get_value(data, "protocol")

        if protocol not in PROTOCOL_MAP:
            continue

        protocols[protocol] = None

        profile = collect_record.profile
        site_id = get_value(data, "sample_event.site", ".")
        if site_id not in site_lookup:
            site_id = DEFAULT_SITE_ID
        mr_id = get_value(data, "sample_event.management", ".")
        if mr_id not in mr_lookup:
            mr_id = DEFAULT_MR_ID

        profile_id = str(profile.pk)

        if site_id not in summary:
            summary[site_id] = {
                "site_name": site_lookup.get(site_id) or DEFAULT_SITE_ID,
                "sample_unit_methods": {protocol: {"profile_summary": {}}},
            }

        if protocol not in summary[site_id]["sample_unit_methods"]:
            summary[site_id]["sample_unit_methods"][protocol] = {"profile_summary": {}}

        if profile_id not in summary[site_id]["sample_unit_methods"][protocol]["profile_summary"]:
            summary[site_id]["sample_unit_methods"][protocol]["profile_summary"][profile_id] = {
                "profile_name": profile.full_name,
                "collect_records": [],
            }

        label = _get_collect_record_label(collect_record)
        sample_date = get_value(data, "sample_event__sample_date")
        mr = mr_lookup.get(mr_id) or DEFAULT_MR_ID
        observers = get_value(data, "observers") or []
        observer_names = [o.get("profile_name") or DEFAULT_OBSERVER_NAME for o in observers]

        summary[site_id]["sample_unit_methods"][protocol]["profile_summary"][profile_id][
            "collect_records"
        ].append(
            {
                "name": label,
                "sample_date": sample_date,
                "management_name": mr,
                "observers": observer_names,
            }
        )

    return list(protocols), summary


def _copy_related_objects(queryset, new_project, track_ids=False):
    """
    If track_ids=True, returns a dict mapping old IDs to new IDs.
    If track_ids=False, uses bulk_create for performance.
    """
    if track_ids:
        id_map = {}
        for obj in queryset:
            old_id = str(obj.id)
            obj.id = None
            obj.project = new_project
            obj.save()
            id_map[old_id] = str(obj.id)
        return id_map
    else:
        objects = []
        for obj in queryset:
            obj.id = None
            obj.project = new_project
            objects.append(obj)
        type(queryset.first()).objects.bulk_create(objects) if objects else None
        return {}


@transaction.atomic()
def copy_project_and_resources(owner_profile, new_project_name, original_project):
    is_demo = str(original_project.pk) == str(settings.DEMO_PROJECT_ID)

    new_project = Project.objects.get(id=original_project.pk)
    new_project.id = None
    new_project.name = new_project_name
    new_project.created_by = owner_profile
    new_project.updated_by = owner_profile
    if is_demo:
        new_project.is_demo = True
    new_project.save()

    new_project.tags.add(*original_project.tags.all())

    ProjectProfile.objects.create(
        role=ProjectProfile.ADMIN, project=new_project, profile=owner_profile
    )

    project_profiles = []
    for pp in original_project.profiles.filter(~Q(profile=owner_profile)):
        pp.id = None
        pp.project = new_project
        project_profiles.append(pp)
    ProjectProfile.objects.bulk_create(project_profiles)

    site_id_map = _copy_related_objects(
        original_project.sites.all(), new_project, track_ids=is_demo
    )
    management_id_map = _copy_related_objects(
        original_project.management_set.all(), new_project, track_ids=is_demo
    )

    if is_demo:
        original_project_fresh = Project.objects.get(id=settings.DEMO_PROJECT_ID)
        copy_project_data(
            original_project=original_project_fresh,
            new_project=new_project,
            owner_profile=owner_profile,
            site_id_map=site_id_map,
            management_id_map=management_id_map,
        )

    return new_project


def copy_project_data(original_project, new_project, owner_profile, site_id_map, management_id_map):
    _copy_collect_records(
        original_project, new_project, owner_profile, site_id_map, management_id_map
    )
    _copy_submitted_data(owner_profile, site_id_map, management_id_map)


def _copy_collect_records(
    original_project, new_project, owner_profile, site_id_map, management_id_map
):
    for cr in original_project.collect_records.all():
        new_data = copy.deepcopy(cr.data) if cr.data else {}

        if new_data.get("sample_event"):
            old_site = new_data["sample_event"].get("site")
            if old_site and str(old_site) in site_id_map:
                new_data["sample_event"]["site"] = site_id_map[str(old_site)]

            old_mgmt = new_data["sample_event"].get("management")
            if old_mgmt and str(old_mgmt) in management_id_map:
                new_data["sample_event"]["management"] = management_id_map[str(old_mgmt)]

        if new_data.get("observers") is not None:
            new_data["observers"] = [{"profile": str(owner_profile.id)}]

        CollectRecord.objects.create(
            project=new_project,
            profile=owner_profile,
            data=new_data,
            validations=copy.deepcopy(cr.validations) if cr.validations else None,
            stage=cr.stage,
            created_by=owner_profile,
            updated_by=owner_profile,
        )


def _copy_submitted_data(owner_profile, site_id_map, management_id_map):
    old_site_ids = [uuid.UUID(k) for k in site_id_map.keys()]
    sample_event_id_map = {}

    for se in SampleEvent.objects.filter(site_id__in=old_site_ids):
        old_se_id = str(se.id)
        se.id = None
        se.site_id = uuid.UUID(site_id_map[str(se.site_id)])
        se.management_id = uuid.UUID(management_id_map[str(se.management_id)])
        se.created_by = owner_profile
        se.updated_by = owner_profile
        se.save()
        sample_event_id_map[old_se_id] = str(se.id)

    _copy_benthic_transects(sample_event_id_map, owner_profile)
    _copy_fish_belt_transects(sample_event_id_map, owner_profile)
    _copy_quadrat_collections(sample_event_id_map, owner_profile)
    _copy_quadrat_transects(sample_event_id_map, owner_profile)


def _copy_benthic_transects(sample_event_id_map, owner_profile):
    """Copy BenthicTransect hierarchy (BenthicLIT, BenthicPIT, HabitatComplexity)."""
    old_se_ids = [uuid.UUID(k) for k in sample_event_id_map.keys()]

    for bt in BenthicTransect.objects.filter(sample_event_id__in=old_se_ids):
        old_bt_id = bt.id
        bt.id = None
        bt.sample_event_id = uuid.UUID(sample_event_id_map[str(bt.sample_event_id)])
        bt.collect_record_id = None
        bt.created_by = owner_profile
        bt.updated_by = owner_profile
        bt.save()

        for lit in BenthicLIT.objects.filter(transect_id=old_bt_id):
            _copy_transect_method(lit, bt.id, owner_profile, ObsBenthicLIT, "benthiclit")

        for pit in BenthicPIT.objects.filter(transect_id=old_bt_id):
            _copy_transect_method(pit, bt.id, owner_profile, ObsBenthicPIT, "benthicpit")

        for hc in HabitatComplexity.objects.filter(transect_id=old_bt_id):
            _copy_transect_method(
                hc, bt.id, owner_profile, ObsHabitatComplexity, "habitatcomplexity"
            )


def _copy_fish_belt_transects(sample_event_id_map, owner_profile):
    """Copy FishBeltTransect hierarchy (BeltFish)."""
    old_se_ids = [uuid.UUID(k) for k in sample_event_id_map.keys()]

    for fbt in FishBeltTransect.objects.filter(sample_event_id__in=old_se_ids):
        old_fbt_id = fbt.id
        fbt.id = None
        fbt.sample_event_id = uuid.UUID(sample_event_id_map[str(fbt.sample_event_id)])
        fbt.collect_record_id = None
        fbt.created_by = owner_profile
        fbt.updated_by = owner_profile
        fbt.save()

        for bf in BeltFish.objects.filter(transect_id=old_fbt_id):
            _copy_transect_method(bf, fbt.id, owner_profile, ObsBeltFish, "beltfish")


def _copy_quadrat_collections(sample_event_id_map, owner_profile):
    """Copy QuadratCollection hierarchy (BleachingQuadratCollection)."""
    old_se_ids = [uuid.UUID(k) for k in sample_event_id_map.keys()]

    for qc in QuadratCollection.objects.filter(sample_event_id__in=old_se_ids):
        old_qc_id = qc.id
        qc.id = None
        qc.sample_event_id = uuid.UUID(sample_event_id_map[str(qc.sample_event_id)])
        qc.collect_record_id = None
        qc.created_by = owner_profile
        qc.updated_by = owner_profile
        qc.save()

        for bqc in BleachingQuadratCollection.objects.filter(quadrat_id=old_qc_id):
            old_bqc_id = bqc.id
            bqc.pk = None
            bqc.id = None
            # Clear the parent pointer for multi-table inheritance
            bqc.transectmethod_ptr_id = None
            bqc.quadrat_id = qc.id
            bqc.collect_record_id = None
            bqc.created_by = owner_profile
            bqc.updated_by = owner_profile
            bqc.save()

            _copy_observations(
                ObsColoniesBleached,
                "bleachingquadratcollection_id",
                old_bqc_id,
                bqc.id,
                owner_profile,
            )
            _copy_observations(
                ObsQuadratBenthicPercent,
                "bleachingquadratcollection_id",
                old_bqc_id,
                bqc.id,
                owner_profile,
            )
            _copy_observer(old_bqc_id, bqc.id, owner_profile)


def _copy_quadrat_transects(sample_event_id_map, owner_profile):
    """Copy QuadratTransect hierarchy (BenthicPhotoQuadratTransect) with images."""
    old_se_ids = [uuid.UUID(k) for k in sample_event_id_map.keys()]

    for qt in QuadratTransect.objects.filter(sample_event_id__in=old_se_ids):
        old_qt_id = qt.id
        qt.id = None
        qt.sample_event_id = uuid.UUID(sample_event_id_map[str(qt.sample_event_id)])
        qt.collect_record_id = None
        qt.created_by = owner_profile
        qt.updated_by = owner_profile
        qt.save()

        for bpqt in BenthicPhotoQuadratTransect.objects.filter(quadrat_transect_id=old_qt_id):
            old_bpqt_id = bpqt.id
            bpqt.pk = None
            bpqt.id = None
            # Clear the parent pointer for multi-table inheritance
            bpqt.transectmethod_ptr_id = None
            bpqt.quadrat_transect_id = qt.id
            bpqt.collect_record_id = None
            bpqt.created_by = owner_profile
            bpqt.updated_by = owner_profile
            bpqt.save()

            # Build image ID map to avoid copying the same image multiple times
            # (multiple observations can reference the same image)
            image_id_map = {}

            for obs in ObsBenthicPhotoQuadrat.objects.filter(
                benthic_photo_quadrat_transect_id=old_bpqt_id
            ):
                old_image_id = obs.image_id
                new_image_id = None

                if old_image_id:
                    if old_image_id not in image_id_map:
                        new_image = _copy_image(obs.image, owner_profile)
                        image_id_map[old_image_id] = new_image.id
                    new_image_id = image_id_map[old_image_id]

                obs.id = None
                obs.benthic_photo_quadrat_transect_id = bpqt.id
                obs.image_id = new_image_id
                obs.created_by = owner_profile
                obs.updated_by = owner_profile
                obs.save()

            _copy_observer(old_bpqt_id, bpqt.id, owner_profile)


def _copy_transect_method(tm, new_transect_id, owner_profile, obs_model, obs_fk_name):
    old_tm_id = tm.id
    tm.pk = None
    tm.id = None
    # Clear the parent pointer for multi-table inheritance
    tm.transectmethod_ptr_id = None
    tm.transect_id = new_transect_id
    tm.collect_record_id = None
    tm.created_by = owner_profile
    tm.updated_by = owner_profile
    tm.save()

    _copy_observations(obs_model, f"{obs_fk_name}_id", old_tm_id, tm.id, owner_profile)
    _copy_observer(old_tm_id, tm.id, owner_profile)


def _copy_observations(obs_model, fk_field, old_parent_id, new_parent_id, owner_profile):
    for obs in obs_model.objects.filter(**{fk_field: old_parent_id}):
        obs.id = None
        setattr(obs, fk_field, new_parent_id)
        obs.created_by = owner_profile
        obs.updated_by = owner_profile
        obs.save()


def _copy_observer(old_tm_id, new_tm_id, owner_profile):
    Observer.objects.create(
        transectmethod_id=new_tm_id,
        profile=owner_profile,
        rank=1,
        created_by=owner_profile,
        updated_by=owner_profile,
    )


def email_members_of_new_project(project, owner_profile):
    for project_profile in project.profiles.filter(~Q(profile=owner_profile)):
        context = {
            "owner": owner_profile,
            "project": project,
            "project_profile": project_profile,
        }
        mermaid_email(
            subject="New Project",
            template="emails/added_to_project.txt",
            to=[project_profile.profile.email],
            context=context,
        )


def get_safe_project_name(project_id):
    try:
        project = Project.objects.get(id=project_id)
        return slugify(project.name, allow_unicode=True).replace("-", "_")
    except Project.DoesNotExist as e:
        raise ValueError(f"Project with id '{project_id}' does not exist") from e


def get_profiles(project):
    return project.profiles.order_by("profile__last_name", "profile__first_name")


def citation_retrieved_text(project_name):
    date_text = timezone.localdate().strftime("%B %-d, %Y")
    domain = settings.DEFAULT_DOMAIN_DASHBOARD
    return f"Retrieved {date_text} from {domain}?project={project_name}."


def default_citation(project, profiles=None):
    if profiles is None:
        profiles = get_profiles(project)
    admin_names = [
        p.profile.citation_name
        for p in profiles
        if p.is_admin is True and p.profile.citation_name is not None
    ]
    year = ""
    latest_se = SampleEvent.objects.filter(site__project=project).order_by("-sample_date").first()
    if latest_se and latest_se.sample_date:
        year = f"{latest_se.sample_date.year}. "
    return f"{', '.join(admin_names)}. {year}{project.name}. MERMAID."


def suggested_citation(project, profiles=None):
    if project is None:
        raise ValueError("Project cannot be None")
    if project.user_citation and project.user_citation.strip():
        return project.user_citation.strip()
    return default_citation(project, profiles)


def delete_project(pk):
    try:
        instance = Project.objects.get(id=pk)
    except Project.DoesNotExist:
        print(f"project {pk} does not exist")
        return

    with transaction.atomic():
        sid = transaction.savepoint()
        try:
            delete_instance_and_related_objects(instance)
            transaction.savepoint_commit(sid)
            print("project deleted")
        except Exception as err:
            print(f"Delete Project: {err}")
            transaction.savepoint_rollback(sid)
