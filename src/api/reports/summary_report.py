import csv
from pyexcelerate import Font, Style, Workbook

from ..models import Covariate, Site
from ..mocks import MockRequest
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
from ..utils.castutils import cast_str_value
from ..utils.timer import timing


aca_benthic_key, aca_benthic_field = Covariate.SUPPORTED_COVARIATES[0]
aca_geomorphic_key, aca_geomorphic_field = Covariate.SUPPORTED_COVARIATES[1]


def _update_covariate_lookup(covar_lookup, site_id, covariates):
    covar_lookup[site_id] = ["", ""]
    for covariate in covariates:
        values = covariate.value
        if values is None:
            continue
        covar_name = covariate.name
        if covar_name == aca_benthic_key:
            values = sorted(values, key=lambda x: (x["area"]), reverse=True)
            covar_lookup[site_id][0] = values[0]["name"] if values else ""
        elif covar_name == aca_geomorphic_key:
            values = sorted(values, key=lambda x: (x["area"]), reverse=True)
            covar_lookup[site_id][1] = values[0]["name"] if values else ""


def _covariate_aca_lookup(site_id_index, content):
    if isinstance(content, list) is False or len(content) < 2:
        return None

    site_ids = list({r[site_id_index] for r in content[1:]})
    sites = Site.objects.filter(id__in=site_ids)
    covar_lookup = {}

    for s in sites:
        covariates = s.covariates.filter(name__in=[aca_benthic_key, aca_geomorphic_key])
        if not covariates:
            continue

        site_id = str(s.id)
        covar_lookup[site_id] = ["", ""]
        _update_covariate_lookup(covar_lookup, site_id, covariates)

    return covar_lookup


def _append_aca_covariates(site_id_index, content, view_serializer):
    """ Append Alan Coral Atlas covariates """

    num_additional_fields = len(view_serializer.additional_fields)
    column_names = [f.display for f in view_serializer.fields]
    column_names.extend([aca_benthic_field, aca_geomorphic_field])

    covariate_lookup = _covariate_aca_lookup(site_id_index, content)
    data = [column_names]
    for row in content[1:]:
        site_id = row[site_id_index]
        covariates = covariate_lookup.get(site_id)
        row = row[0:-1 * num_additional_fields]
        if covariates:
            row.extend(covariates)
        data.append(row)
    
    return data


def get_viewset_csv_content(view_cls, project_pk, request):
    request = MockRequest()
    kwargs = {"project_pk": project_pk, "use_cached": False}
    vw = view_cls(**kwargs)
    vw.kwargs = kwargs
    vw.request = request
    resp = vw.csv(request)
    content = list(
        csv.reader([str(row, "UTF-8").strip() for row in resp.streaming_content])
    )
    if isinstance(content, list) is False or len(content) < 2 or "site_id" not in content[0]:
        return content

    site_id_index = content[0].index("site_id")
    if site_id_index is None:
        return content
    
    return _append_aca_covariates(
        site_id_index,
        content,
        view_cls.serializer_class_csv
    )


def write_data(wb, sheet_name, data):
    casted_data = []
    for row in data:
        casted_row = [cast_str_value(col) for col in row]
        casted_data.append(casted_row)

    ws = wb.new_sheet(sheet_name, data=casted_data)
    ws.set_row_style(1, Style(font=Font(bold=True)))


@timing
def _create_report(request, project_pk, views, sheet_names):
    wb = Workbook()
    for view, sheet_name in zip(views, sheet_names):
        content = get_viewset_csv_content(view, project_pk, request)
        write_data(wb, sheet_name, content)

    return wb


def create_belt_fish_report(request, project_pk):
    return _create_report(
        request,
        project_pk,
        views=[
            BeltFishProjectMethodSEView,
            BeltFishProjectMethodSUView,
            BeltFishProjectMethodObsView,
        ],
        sheet_names=[
            "Belt Fish SE",
            "Belt Fish SU",
            "Belt Fish Obs",
        ],
    )


def create_benthic_pit_report(request, project_pk):
    return _create_report(
        request,
        project_pk,
        views=[
            BenthicPITProjectMethodSEView,
            BenthicPITProjectMethodSUView,
            BenthicPITProjectMethodObsView,
        ],
        sheet_names=[
            "Benthic PIT SE",
            "Benthic PIT SU",
            "Benthic PIT Obs",
        ],
    )


def create_benthic_lit_report(request, project_pk):
    return _create_report(
        request,
        project_pk,
        views=[
            BenthicLITProjectMethodSEView,
            BenthicLITProjectMethodObsView,
            BenthicLITProjectMethodSUView,
        ],
        sheet_names=[
            "Benthic LIT SE",
            "Benthic LIT SU",
            "Benthic LIT Obs",
        ],
    )


def create_bleaching_qc_report(request, project_pk):
    return _create_report(
        request,
        project_pk,
        views=[
            BleachingQCProjectMethodSEView,
            BleachingQCProjectMethodSUView,
            BleachingQCProjectMethodObsColoniesBleachedView,
            BleachingQCProjectMethodObsQuadratBenthicPercentView,
        ],
        sheet_names=[
            "Bleaching QT SE",
            "Bleaching QT SU",
            "BQT Colonies Bleached Obs",
            "BQT Quad Benthic Percent Obs",
        ],
    )


def create_benthic_pqt_report(request, project_pk):
    return _create_report(
        request,
        project_pk,
        views=[
            BenthicPQTProjectMethodSEView,
            BenthicPQTProjectMethodSUView,
            BenthicPQTProjectMethodObsView,
        ],
        sheet_names=[
            "Benthic PQT SE",
            "Benthic PQT SU",
            "Benthic PQT Obs",
        ],
    )


def create_habitat_complexity_report(request, project_pk):
    return _create_report(
        request,
        project_pk,
        views=[
            HabitatComplexityProjectMethodSEView,
            HabitatComplexityProjectMethodSUView,
            HabitatComplexityProjectMethodObsView,
        ],
        sheet_names=[
            "Habitat Complexity SE",
            "Habitat Complexity SU",
            "Habitat Complexity Obs",
        ],
    )
