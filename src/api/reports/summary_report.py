import csv
from collections import defaultdict
from typing import Dict, List, Set, Tuple

import pandas as pd
from django.db.models import QuerySet

from ..exceptions import UnknownProtocolError
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
    Site,
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
from ..utils import cached
from ..utils.timer import timing
from . import xl

ACA_BENTHIC_KEY, ACA_BENTHIC_FIELD = Covariate.SUPPORTED_COVARIATES[0]
ACA_GEOMORPHIC_KEY, ACA_GEOMORPHIC_FIELD = Covariate.SUPPORTED_COVARIATES[1]

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
        print(resp.content)
        raise ValueError(f"Failed to get content for project {project_pk}")

    content = list(csv.reader([str(row, "UTF-8").strip() for row in resp.streaming_content]))
    if not isinstance(content, list) or len(content) < 2 or "site_id" not in content[0]:
        if isinstance(content, list):
            yield from content
        return

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
    yield from filtered_rows


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
    projects = Project.objects.filter(pk__in=project_ids)
    prj_serializer = ProjectCSVSerializer(projects, show_display_fields=True)
    header = [f.display for f in prj_serializer.fields]
    data = [list(r.values()) for r in prj_serializer.data]
    _inject_protocol_viewability(header, data, viewable_levels)
    return [header] + data


def _df_to_rows(df):
    yield list(df.columns)
    for _, row in df.iterrows():
        yield row.tolist()


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

    # Protocol data - collect all data first, then concatenate and write
    sheet_data = {sheet_name: [] for sheet_name in sheet_names}

    # Collect data for each project and view
    for project_id in project_ids:
        project_id = str(project_id)
        config = report_config[project_id]
        views = config["views"]
        project_sheet_names = config["sheet_names"]
        for view, sheet_name in zip(views, project_sheet_names):
            data = get_viewset_csv_content(view, project_id, request)
            rows = list(data)
            if rows:
                df = (
                    pd.DataFrame(rows[1:], columns=rows[0])
                    if len(rows) > 1
                    else pd.DataFrame(columns=rows[0])
                )
                sheet_data[sheet_name].append(df)

    # Concatenate data for each sheet and write to workbook
    for sheet_name in sheet_names:
        if sheet_data[sheet_name]:
            combined_df = pd.concat(sheet_data[sheet_name], ignore_index=True)
            xl.write_data_to_sheet(
                workbook=wb, sheet_name=sheet_name, data=_df_to_rows(combined_df), row=1, col=1
            )
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
