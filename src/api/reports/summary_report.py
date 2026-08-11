import csv
import gzip
import itertools
import logging
from collections import defaultdict

from ..exceptions import UnknownProtocolError
from ..mocks import MockRequest
from ..models import (
    BENTHICLIT_PROTOCOL,
    BENTHICPIT_PROTOCOL,
    BENTHICPQT_PROTOCOL,
    BLEACHINGQC_PROTOCOL,
    FISHBELT_PROTOCOL,
    HABITATCOMPLEXITY_PROTOCOL,
    MACROINVERTEBRATE_PROTOCOL,
    Project,
    ProjectProfile,
)
from ..resources.project import ProjectCSVSerializer, annotate_num_sample_units
from ..resources.sampleunitmethods.beltfishmethod import (
    BeltFishProjectMethodObsView,
    BeltFishProjectMethodSEView,
    BeltFishProjectMethodSUView,
)
from ..resources.sampleunitmethods.beltinvertmethod import (
    BeltInvertProjectMethodObsView,
    BeltInvertProjectMethodSEView,
    BeltInvertProjectMethodSUView,
)
from ..resources.sampleunitmethods.benthiclitmethod import (
    BenthicLITProjectMethodObsView,
    BenthicLITProjectMethodSEView,
    BenthicLITProjectMethodSUView,
)
from ..resources.sampleunitmethods.benthicphotoquadrattransectmethod import (
    BenthicPQTProjectMethodObsView,
    BenthicPQTProjectMethodSEView,
    BenthicPQTProjectMethodSUView,
)
from ..resources.sampleunitmethods.benthicpitmethod import (
    BenthicPITProjectMethodObsView,
    BenthicPITProjectMethodSEView,
    BenthicPITProjectMethodSUView,
)
from ..resources.sampleunitmethods.bleachingquadratcollectionmethod import (
    BleachingQCProjectMethodObsColoniesBleachedView,
    BleachingQCProjectMethodObsQuadratBenthicPercentView,
    BleachingQCProjectMethodSEView,
    BleachingQCProjectMethodSUView,
)
from ..resources.sampleunitmethods.habitatcomplexitymethod import (
    HabitatComplexityProjectMethodObsView,
    HabitatComplexityProjectMethodSEView,
    HabitatComplexityProjectMethodSUView,
)
from ..utils import cached
from ..utils.timer import timing
from . import xl

logger = logging.getLogger(__name__)

PROJECT_MEMBER = "project_member"


# Mapping of protocols to their respective views and sheet names
PROTOCOL_VIEW_MAPPING = {
    BENTHICLIT_PROTOCOL: {
        "views": [
            BenthicLITProjectMethodSEView,
            BenthicLITProjectMethodSUView,
            BenthicLITProjectMethodObsView,
        ],
        "sheet_names": ["Benthic LIT SE", "Benthic LIT SU", "Benthic LIT Obs"],
    },
    BENTHICPIT_PROTOCOL: {
        "views": [
            BenthicPITProjectMethodSEView,
            BenthicPITProjectMethodSUView,
            BenthicPITProjectMethodObsView,
        ],
        "sheet_names": ["Benthic PIT SE", "Benthic PIT SU", "Benthic PIT Obs"],
    },
    FISHBELT_PROTOCOL: {
        "views": [
            BeltFishProjectMethodSEView,
            BeltFishProjectMethodSUView,
            BeltFishProjectMethodObsView,
        ],
        "sheet_names": ["Belt Fish SE", "Belt Fish SU", "Belt Fish Obs"],
    },
    BLEACHINGQC_PROTOCOL: {
        "views": [
            BleachingQCProjectMethodSEView,
            BleachingQCProjectMethodSUView,
            BleachingQCProjectMethodObsColoniesBleachedView,
            BleachingQCProjectMethodObsQuadratBenthicPercentView,
        ],
        "sheet_names": [
            "Bleaching QT SE",
            "Bleaching QT SU",
            "BQT Colonies Bleached Obs",
            "BQT Quad Benthic Percent Obs",
        ],
    },
    BENTHICPQT_PROTOCOL: {
        "views": [
            BenthicPQTProjectMethodSEView,
            BenthicPQTProjectMethodSUView,
            BenthicPQTProjectMethodObsView,
        ],
        "sheet_names": ["Benthic PQT SE", "Benthic PQT SU", "Benthic PQT Obs"],
    },
    HABITATCOMPLEXITY_PROTOCOL: {
        "views": [
            HabitatComplexityProjectMethodSEView,
            HabitatComplexityProjectMethodSUView,
            HabitatComplexityProjectMethodObsView,
        ],
        "sheet_names": ["Habitat Complexity SE", "Habitat Complexity SU", "Habitat Complexity Obs"],
    },
    MACROINVERTEBRATE_PROTOCOL: {
        "views": [
            BeltInvertProjectMethodSEView,
            BeltInvertProjectMethodSUView,
            BeltInvertProjectMethodObsView,
        ],
        "sheet_names": ["Macroinvertebrate SE", "Macroinvertebrate SU", "Macroinvertebrate Obs"],
    },
}


def get_viewset_csv_content(view_cls, project_pk, request):
    key = cached.make_viewset_cache_key(
        view_cls,
        project_pk,
        include_additional_fields=False,
        show_display_fields=True,
    )
    cached_file = cached.get_cached_textfile(key)
    if cached_file:
        for row in csv.reader(cached_file):
            yield row
        return

    # Mocking a required request object so we can call viewset action.
    request = MockRequest()
    request.query_params["field_report"] = True
    kwargs = {"project_pk": project_pk, "use_cached": False}
    vw = view_cls(**kwargs)
    vw.kwargs = kwargs
    vw.request = request
    resp = vw.csv(request)

    if resp.status_code != 200:
        logger.error(
            "Failed to get CSV content for project %s: %s",
            project_pk,
            b"".join(resp.streaming_content),
        )
        raise ValueError(f"Failed to get content for project {project_pk}")

    raw_bytes = b"".join(resp.streaming_content)
    if resp.get("Content-Encoding") == "gzip":
        raw_bytes = gzip.decompress(raw_bytes)
    content = list(csv.reader(raw_bytes.decode("utf-8").splitlines()))
    yield from content


def _find_project_id(headers, data_row):
    for n, header in enumerate(headers):
        if header == "Project Id":
            return data_row[n]
    return None


def _inject_protocol_viewability(header, data, viewable_levels):
    # Insert columns for Sample Events, Sample Units, Observations, and Export user in project
    for n, _ in enumerate(data):
        project_id = _find_project_id(header, data[n])
        viewable_level = viewable_levels.get(project_id)
        if project_id is None:
            data[n].insert(4, "-")
            data[n].insert(5, "-")
            data[n].insert(6, "-")
            data[n].insert(7, "-")
        elif viewable_level == Project.PUBLIC:
            data[n].insert(4, "Yes")
            data[n].insert(5, "Yes")
            data[n].insert(6, "Yes")
            data[n].insert(7, "No")
        elif viewable_level == PROJECT_MEMBER:
            data[n].insert(4, "Yes")
            data[n].insert(5, "Yes")
            data[n].insert(6, "Yes")
            data[n].insert(7, "Yes")
        elif viewable_level == Project.PUBLIC_SUMMARY:
            data[n].insert(4, "Yes")
            data[n].insert(5, "No")
            data[n].insert(6, "No")
            data[n].insert(7, "No")
        else:
            data[n].insert(4, "No")
            data[n].insert(5, "No")
            data[n].insert(6, "No")
            data[n].insert(7, "No")

    # Insert header columns
    header.insert(4, "Sample Events")
    header.insert(5, "Sample Units")
    header.insert(6, "Observations")
    header.insert(7, "Export user in project")


def _get_project_metadata(project_ids, viewable_levels):
    projects = annotate_num_sample_units(Project.objects.filter(pk__in=project_ids))
    prj_serializer = ProjectCSVSerializer(projects, show_display_fields=True)
    header = [f.display for f in prj_serializer.fields]
    data = [list(r.values()) for r in prj_serializer.data]
    _inject_protocol_viewability(header, data, viewable_levels)
    return [header] + data


@timing
def create_protocol_report(request, project_ids, protocol):
    """
    Generic function to create a report for any protocol based on the provided mapping.
    """

    wb = xl.get_workbook(f"{protocol}_summary")

    # Fetch the appropriate views and sheet names based on the protocol
    protocol_config = PROTOCOL_VIEW_MAPPING.get(protocol)

    if not protocol_config:
        raise UnknownProtocolError(f"Unknown protocol [{protocol}]")

    views = protocol_config["views"]
    sheet_names = protocol_config["sheet_names"]
    viewable_levels = get_project_protocol_viewable_level(request, protocol, project_ids)

    report_config = defaultdict(dict)
    for project_id, viewable_level in viewable_levels.items():
        if viewable_level == Project.PUBLIC_SUMMARY:
            # Only SE views for public summary
            report_config[project_id]["views"] = views[:1]
            report_config[project_id]["sheet_names"] = sheet_names[:1]
        elif viewable_level == Project.PUBLIC or viewable_level == PROJECT_MEMBER:
            # See all views
            report_config[project_id]["views"] = views
            report_config[project_id]["sheet_names"] = sheet_names
        else:
            # No views for private
            report_config[project_id]["views"] = []
            report_config[project_id]["sheet_names"] = []

    # Metadata
    project_metadata = _get_project_metadata(project_ids, viewable_levels)
    xl.write_data_to_sheet(wb, "Metadata", project_metadata, 1, 1)
    xl.auto_size_columns(wb["Metadata"])

    # Protocol data - stream each project directly to workbook
    sheet_rows = {sheet_name: 1 for sheet_name in sheet_names}
    headers_written = set()

    for project_id in project_ids:
        project_id = str(project_id)
        config = report_config[project_id]
        for view, sheet_name in zip(config["views"], config["sheet_names"]):
            rows_iter = iter(get_viewset_csv_content(view, project_id, request))
            first_row = next(rows_iter, None)
            if first_row is None:
                continue
            if sheet_name not in headers_written:
                headers_written.add(sheet_name)
                rows_to_write = itertools.chain([first_row], rows_iter)
            else:
                # first_row is the header; skip it and check for data
                data_first = next(rows_iter, None)
                if data_first is None:
                    continue
                rows_to_write = itertools.chain([data_first], rows_iter)
            last_row, _ = xl.write_data_to_sheet(
                workbook=wb,
                sheet_name=sheet_name,
                data=rows_to_write,
                row=sheet_rows[sheet_name],
                col=1,
            )
            sheet_rows[sheet_name] = last_row + 1

    for sheet_name in sheet_names:
        if sheet_name in wb.sheetnames:
            xl.auto_size_columns(wb[sheet_name])

    return wb


def get_project_protocol_viewable_level(request, protocol, project_ids):
    viewable_levels = {}
    profile = request.user.profile

    data_policy_field_name = Project.get_sample_unit_method_policy(protocol)

    projects = Project.objects.filter(pk__in=project_ids)
    project_profiles = ProjectProfile.objects.filter(profile=profile, project__in=projects)
    project_lookup = [pp.project_id for pp in project_profiles]

    for project in projects:
        project_id = str(project.pk)
        if project.pk in project_lookup:
            viewable_levels[project_id] = PROJECT_MEMBER
        else:
            viewable_levels[project_id] = getattr(project, data_policy_field_name)

    return viewable_levels
