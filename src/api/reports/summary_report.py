import csv
from pyexcelerate import Font, Style, Workbook

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


def get_viewset_csv_content(view_cls, project_pk, request):
    request = MockRequest(query_params={"field_report": "t"})
    vw = view_cls()
    vw.kwargs = {"project_pk": project_pk}
    vw.request = request
    resp = vw.csv(request, **vw.kwargs)
    return list(
        csv.reader([str(row, "UTF-8").strip() for row in resp.streaming_content])
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
