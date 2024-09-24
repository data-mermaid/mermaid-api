import csv
from typing import Dict, List, Set, Tuple

from django.db.models import QuerySet

from . import xl
from ..mocks import MockRequest
from ..models import (
    BENTHICLIT_PROTOCOL,
    BENTHICPIT_PROTOCOL,
    BENTHICPQT_PROTOCOL,
    BLEACHINGQC_PROTOCOL,
    FISHBELT_PROTOCOL,
    HABITATCOMPLEXITY_PROTOCOL,
    Covariate,
    Project,
    ProjectProfile,
    Site
)
from ..resources.project import ProjectCSVSerializer
from ..resources.sampleunitmethods.beltfishmethod import (
    BeltFishProjectMethodObsView,
    BeltFishProjectMethodSEView,
    BeltFishProjectMethodSUView,
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
from ..utils.timer import timing

ACA_BENTHIC_KEY, ACA_BENTHIC_FIELD = Covariate.SUPPORTED_COVARIATES[0]
ACA_GEOMORPHIC_KEY, ACA_GEOMORPHIC_FIELD = Covariate.SUPPORTED_COVARIATES[1]


# Mapping of protocols to their respective views and sheet names
PROTOCOL_VIEW_MAPPING = {
    BENTHICLIT_PROTOCOL: {
        "views": [BenthicLITProjectMethodSEView, BenthicLITProjectMethodSUView, BenthicLITProjectMethodObsView],
        "sheet_names": ["Benthic LIT SE", "Benthic LIT SU", "Benthic LIT Obs"],
    },
    BENTHICPIT_PROTOCOL: {
        "views": [BenthicPITProjectMethodSEView, BenthicPITProjectMethodSUView, BenthicPITProjectMethodObsView],
        "sheet_names": ["Benthic PIT SE", "Benthic PIT SU", "Benthic PIT Obs"],
    },
    FISHBELT_PROTOCOL: {
        "views": [BeltFishProjectMethodSEView, BeltFishProjectMethodSUView, BeltFishProjectMethodObsView],
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
        "views": [BenthicPQTProjectMethodSEView, BenthicPQTProjectMethodSUView, BenthicPQTProjectMethodObsView],
        "sheet_names": ["Benthic PQT SE", "Benthic PQT SU", "Benthic PQT Obs"],
    },
    HABITATCOMPLEXITY_PROTOCOL: {
        "views": [HabitatComplexityProjectMethodSEView, HabitatComplexityProjectMethodSUView, HabitatComplexityProjectMethodObsView],
        "sheet_names": ["Habitat Complexity SE", "Habitat Complexity SU", "Habitat Complexity Obs"],
    },
}


def _sort_covariate_value(values):
    return sorted(values, key=lambda x: (x.get("area") or 0.0), reverse=True)


def _update_covariate_lookup(
    covar_lookup: Dict[str, list], site_id: str, covariates: QuerySet[Covariate]
) -> None:
    covar_lookup[site_id] = ["", ""]
    for covariate in covariates:
        values = covariate.value
        if values is None:
            continue

        covar_name = covariate.name
        if covar_name == ACA_BENTHIC_KEY:
            values = _sort_covariate_value(values)
            covar_lookup[site_id][0] = values[0].get("name") if values else ""
        elif covar_name == ACA_GEOMORPHIC_KEY:
            values = _sort_covariate_value(values)
            covar_lookup[site_id][1] = values[0].get("name") if values else ""


def _covariate_aca_lookup(site_ids: List[str]) -> Dict[str, List[str]]:
    sites = Site.objects.filter(id__in=site_ids)
    covar_lookup = {}

    for s in sites:
        covariates = s.covariates.filter(name__in=[ACA_BENTHIC_KEY, ACA_GEOMORPHIC_KEY])
        site_id = str(s.id)
        _update_covariate_lookup(covar_lookup, site_id, covariates)

    return covar_lookup


def _get_site_aca_covariate_columns(site_ids: List[str]) -> Tuple[list, list]:
    """Allen Coral Atlas covariates

    Args:
        site_ids (list): List of site ids for lookup up covariate values.

    Returns:
        [tuple]: ACA Benthic and Geomorphic values for each site.
    """

    covariate_lookup = _covariate_aca_lookup(site_ids)
    aca_benthics = []
    aca_geomorphics = []
    for site_id in site_ids:
        aca_benthic, aca_geomorphic = covariate_lookup.get(site_id) or ["", ""]
        aca_benthics.append(aca_benthic)
        aca_geomorphics.append(aca_geomorphic)

    return aca_benthics, aca_geomorphics


def _match_length(key, substring):
    """Return the length of the matching prefix."""
    length = min(len(key), len(substring))
    for i in range(length):
        if key[i] != substring[i]:
            return i
    return length


def _partial_key_match(d: dict, substring):
    """Match dictionary key characters in substring.

    Args:
        d (dict): Dictionary
        substring ([type]): String to match.

    Returns:
        list: Returns dictionary key matches.  List is ordered by number of character matches.
    """
    matches = [(key, _match_length(key, substring)) for key in d.keys()]
    matches.sort(key=lambda x: (-x[1], x[0]))
    return [key for key, length in matches if length > 0]


def _transpose(data: list):
    return list(zip(*data))


def _filter_columns(
    headers: List[str],
    cols: List[list],
    display_header_lookup: Dict[str, None],
    additional_header_lookup: Set[str],
) -> Tuple[List[str], List[list]]:
    new_headers = []
    new_cols = []

    # Remove site_id, it was only needed to attach
    # covariates to the content.
    additional_header_lookup = list(additional_header_lookup)
    additional_header_lookup.append("site_id")
    for header, col in zip(headers, cols):
        if header in additional_header_lookup:
            continue
        elif header in display_header_lookup:
            new_headers.append(display_header_lookup[header])
            new_cols.append(col)
        else:
            matches = _partial_key_match(display_header_lookup, header)
            if len(matches) > 1:
                h = header[len(matches[0]) + 1 :]
                new_headers.append(h)
            else:
                new_headers.append(header)
            new_cols.append(col)

    return new_headers, new_cols


def get_viewset_csv_content(view_cls, project_pk, request):
    # Mocking a required request object so we can call viewset action.
    request = MockRequest()
    request.query_params["field_report"] = True
    kwargs = {"project_pk": project_pk, "use_cached": False}
    vw = view_cls(**kwargs)
    vw.kwargs = kwargs
    vw.request = request
    resp = vw.csv(request)
    content = list(csv.reader([str(row, "UTF-8").strip() for row in resp.streaming_content]))
    if not isinstance(content, list) or len(content) < 2 or "site_id" not in content[0]:
        return content

    headers = content[0]
    cols = _transpose(content[1:])

    site_id_index = content[0].index("site_id")
    if site_id_index is not None:
        site_ids = cols[site_id_index]
        # Add Alan Coral Atlas covariates
        aca_benthic_col, aca_geomorphic_col = _get_site_aca_covariate_columns(site_ids)
        headers.extend([ACA_BENTHIC_FIELD, ACA_GEOMORPHIC_FIELD])
        cols.extend([aca_benthic_col, aca_geomorphic_col])

    # Create lookups to help with filtering output header columns.
    display_header_lookup = {
        f.alias or f.column_path: f.display for f in view_cls.serializer_class_csv.fields
    }
    display_header_lookup[ACA_BENTHIC_FIELD] = ACA_BENTHIC_FIELD
    display_header_lookup[ACA_GEOMORPHIC_FIELD] = ACA_GEOMORPHIC_FIELD
    additional_header_lookup = {
        f.alias or f.column_path
        for f in view_cls.serializer_class_csv.additional_fields
        if f.column_path in headers
    }
    new_headers, new_cols = _filter_columns(
        headers, cols, display_header_lookup, additional_header_lookup
    )

    new_rows = _transpose(new_cols)
    filtered_rows = [new_headers] + new_rows

    return filtered_rows


def _get_project_metadata(project_ids):
    projects = Project.objects.filter(pk__in=project_ids)
    prj_serializer = ProjectCSVSerializer(projects, show_display_fields=True)
    header = [f.display for f in prj_serializer.fields]
    return [header] + [r.values() for r in prj_serializer.data]


@timing
def create_protocol_report(request, project_ids, protocol, data_policy_level=Project.PRIVATE):
    """
    Generic function to create a report for any protocol based on the provided mapping.
    """

    wb = xl.get_workbook(f"{protocol}_summary")
    
    # Fetch the appropriate views and sheet names based on the protocol
    protocol_config = PROTOCOL_VIEW_MAPPING.get(protocol)
    
    if not protocol_config:
        raise ValueError(f"Unknown protocol [{protocol}]")

    views = protocol_config['views']
    sheet_names = protocol_config['sheet_names']

    if data_policy_level == Project.PUBLIC_SUMMARY:
        # Only SE views for public summary
        views = views[:1]
        sheet_names = sheet_names[:1]
    elif data_policy_level == Project.PRIVATE:
        # No views for private
        views = []
        sheet_names = []

    # Metadata
    project_metadata = _get_project_metadata(project_ids)
    xl.write_data_to_sheet(wb, "Metadata", project_metadata, 1, 1)
    xl.auto_size_columns(wb["Metadata"])

    # Protocol data
    for view, sheet_name in zip(views, sheet_names):
        current_row = 1
        existing_row = current_row
        
        for project_id in project_ids:
            data = get_viewset_csv_content(view, project_id, request)
            if current_row > 1:
                data = data[1:]  # Skip headers for subsequent projects

            existing_row = current_row
            current_row, _ = xl.write_data_to_sheet(
                workbook=wb,
                sheet_name=sheet_name,
                data=data,
                row=existing_row,
                col=1
            )
            if current_row > existing_row:
                current_row = existing_row + 1

        xl.auto_size_columns(wb[sheet_name])
    
    return wb


def check_su_method_policy_level(
    request,
    protocol,
    project_ids
):
    data_policy_levels = []
    profile = request.user.profile

    data_policy_field_name = Project.get_sample_unit_method_policy(protocol)

    projects = Project.objects.filter(pk__in=project_ids)
    project_profiles = ProjectProfile.objects.filter(profile=profile, project__in=projects)
    project_lookup = [pp.project_id for pp in project_profiles]

    for project in projects:
        if project.pk in project_lookup:
            data_policy_levels.append(Project.PUBLIC)
        else:
            data_policy_levels.append(getattr(project, data_policy_field_name))

    if Project.PRIVATE in data_policy_levels:
        return Project.PRIVATE
    elif all(item == Project.PUBLIC for item in data_policy_levels):
        return Project.PUBLIC
    
    return Project.PUBLIC_SUMMARY
