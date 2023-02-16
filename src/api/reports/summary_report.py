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
    ws = wb.new_sheet(sheet_name, data=data)
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
            BeltFishProjectMethodObsView,
            BeltFishProjectMethodSUView,
            BeltFishProjectMethodSEView,
        ],
        sheet_names=[
            "Belt Fish Obs",
            "Belt Fish SU",
            "Belt Fish SE",
        ],
    )


def create_benthic_pit_report(request, project_pk):
    return _create_report(
        request,
        project_pk,
        views=[
            BenthicPITProjectMethodObsView,
            BenthicPITProjectMethodSUView,
            BenthicPITProjectMethodSEView,
        ],
        sheet_names=[
            "Benthic PIT Obs",
            "Benthic PIT SU",
            "Benthic PIT SE",
        ],
    )


def create_benthic_lit_report(request, project_pk):
    return _create_report(
        request,
        project_pk,
        views=[
            BenthicLITProjectMethodObsView,
            BenthicLITProjectMethodSUView,
            BenthicLITProjectMethodSEView,
        ],
        sheet_names=[
            "Benthic LIT Obs",
            "Benthic LIT SU",
            "Benthic LIT SE",
        ],
    )


def create_bleaching_qc_report(request, project_pk):
    return _create_report(
        request,
        project_pk,
        views=[
            BleachingQCProjectMethodObsColoniesBleachedView,
            BleachingQCProjectMethodObsQuadratBenthicPercentView,
            BleachingQCProjectMethodSUView,
            BleachingQCProjectMethodSEView,
        ],
        sheet_names=[
            "BQT Colonies Bleached Obs",
            "BQT Quad Benthic Percent Obs",
            "Bleaching QT SU",
            "Bleaching QT SE",
        ],
    )


def create_benthic_pqt_report(request, project_pk):
    return _create_report(
        request,
        project_pk,
        views=[
            BenthicPQTProjectMethodObsView,
            BenthicPQTProjectMethodSUView,
            BenthicPQTProjectMethodSEView,
        ],
        sheet_names=[
            "Benthic PQT Obs",
            "Benthic PQT SU",
            "Benthic PQT SE",
        ],
    )


def create_habitat_complexity_report(request, project_pk):
    return _create_report(
        request,
        project_pk,
        views=[
            HabitatComplexityProjectMethodObsView,
            HabitatComplexityProjectMethodSUView,
            HabitatComplexityProjectMethodSEView,
        ],
        sheet_names=[
            "Habitat Complexity Obs",
            "Habitat Complexity SU",
            "Habitat Complexity SE",
        ],
    )
