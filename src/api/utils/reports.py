from tempfile import NamedTemporaryFile

from django.conf import settings

from ..mocks import MockRequest
from ..models import (
    BENTHICLIT_PROTOCOL,
    BENTHICPIT_PROTOCOL,
    BENTHICPQT_PROTOCOL,
    BLEACHINGQC_PROTOCOL,
    FISHBELT_PROTOCOL,
    HABITATCOMPLEXITY_PROTOCOL,
)
from ..reports import attributes_report
from ..reports.summary_report import (
    create_belt_fish_report,
    create_benthic_lit_report,
    create_benthic_pit_report,
    create_benthic_pqt_report,
    create_bleaching_qc_report,
    create_habitat_complexity_report,
)
from . import s3


def update_attributes_report():
    with NamedTemporaryFile() as tmp:
        attributes_report.write_attribute_reference(tmp.name)
        s3.upload_file(settings.PUBLIC_BUCKET, tmp.name, "mermaid_attributes.xlsx")


def create_sample_unit_method_summary_report(project_pk, protocol, output_path, request=None):
    request = request or MockRequest()

    if protocol == BENTHICLIT_PROTOCOL:
        wb = create_benthic_lit_report(request, project_pk)
    elif protocol == BENTHICPIT_PROTOCOL:
        wb = create_benthic_pit_report(request, project_pk)
    elif protocol == FISHBELT_PROTOCOL:
        wb = create_belt_fish_report(request, project_pk)
    elif protocol == HABITATCOMPLEXITY_PROTOCOL:
        wb = create_habitat_complexity_report(request, project_pk)
    elif protocol == BLEACHINGQC_PROTOCOL:
        wb = create_bleaching_qc_report(request, project_pk)
    elif protocol == BENTHICPQT_PROTOCOL:
        wb = create_benthic_pqt_report(request, project_pk)
    else:
        raise ValueError(f"Unknown protocol [{protocol}]")

    wb.save(output_path)

    return output_path
