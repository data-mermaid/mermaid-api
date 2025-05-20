import csv
import logging
from tempfile import NamedTemporaryFile

from ..exceptions import UpdateSummariesException
from ..mocks import MockRequest
from ..models import (
    BENTHICLIT_PROTOCOL,
    BENTHICPIT_PROTOCOL,
    BENTHICPQT_PROTOCOL,
    BLEACHINGQC_PROTOCOL,
    FISHBELT_PROTOCOL,
    HABITATCOMPLEXITY_PROTOCOL,
    Project,
)
from ..reports import csv_report
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
from ..resources.summary_sample_event import SummarySampleEventView
from ..utils import cached
from ..utils.timer import timing

logger = logging.getLogger(__name__)


def _update_cached_csv(
    project_id,
    viewset_cls,
    skip_updates=False,
    include_additional_fields=False,
    show_display_fields=False,
):
    assert hasattr(viewset_cls, "serializer_class_csv")

    key = cached.make_viewset_cache_key(
        viewset_cls,
        project_id,
        include_additional_fields=include_additional_fields,
        show_display_fields=show_display_fields,
    )

    if skip_updates is not True:
        cached.delete_file(key)

    request = MockRequest()

    vw = viewset_cls()
    vw.kwargs = {"project_pk": project_id}
    vw.request = request
    qs = vw.get_queryset().filter(project_id=project_id)
    fields, rows = csv_report.get_formatted_data(
        qs,
        serializer_class=viewset_cls.serializer_class_csv,
        include_additional_fields=include_additional_fields,
        show_display_fields=show_display_fields,
    )
    with NamedTemporaryFile(mode="w") as csvfile:
        writer = csv.writer(csvfile, quoting=csv.QUOTE_ALL)
        writer.writerow(fields)
        writer.writerows(rows)
        csvfile.flush()
        cached.cache_file(key, csvfile.name, compress=True, content_type="text/csv")


def _update_cached_csvs(project_id, viewset_cls, skip_updates=False):
    # CSV with user-friendly field names
    _update_cached_csv(
        project_id,
        viewset_cls,
        skip_updates=skip_updates,
        include_additional_fields=False,
        show_display_fields=True,
    )

    # CSV with additional fields and variable column names
    _update_cached_csv(
        project_id,
        viewset_cls,
        skip_updates=skip_updates,
        include_additional_fields=True,
        show_display_fields=False,
    )


@timing
def update_summary_csv_cache(project_id, sample_unit=None, skip_test_project=False):
    skip_updates = False
    if (
        skip_test_project is True
        and Project.objects.filter(id=project_id, status=Project.TEST).exists()
    ):
        skip_updates = True

    print("---- RUNNING CACHE UPDATE ----")
    try:
        if sample_unit is None or sample_unit == FISHBELT_PROTOCOL:
            _update_cached_csvs(project_id, BeltFishProjectMethodObsView, skip_updates)
            _update_cached_csvs(project_id, BeltFishProjectMethodSUView, skip_updates)
            _update_cached_csvs(project_id, BeltFishProjectMethodSEView, skip_updates)

        if sample_unit is None or sample_unit == BENTHICLIT_PROTOCOL:
            _update_cached_csvs(project_id, BenthicLITProjectMethodObsView, skip_updates)
            _update_cached_csvs(project_id, BenthicLITProjectMethodSUView, skip_updates)
            _update_cached_csvs(project_id, BenthicLITProjectMethodSEView, skip_updates)

        if sample_unit is None or sample_unit == BENTHICPIT_PROTOCOL:
            _update_cached_csvs(project_id, BenthicPITProjectMethodObsView, skip_updates)
            _update_cached_csvs(project_id, BenthicPITProjectMethodSUView, skip_updates)
            _update_cached_csvs(project_id, BenthicPITProjectMethodSEView, skip_updates)

        if sample_unit is None or sample_unit == BENTHICPQT_PROTOCOL:
            _update_cached_csvs(project_id, BenthicPQTProjectMethodObsView, skip_updates)
            _update_cached_csvs(project_id, BenthicPQTProjectMethodSUView, skip_updates)
            _update_cached_csvs(project_id, BenthicPQTProjectMethodSEView, skip_updates)

        if sample_unit is None or sample_unit == BLEACHINGQC_PROTOCOL:
            _update_cached_csvs(
                project_id, BleachingQCProjectMethodObsColoniesBleachedView, skip_updates
            )
            _update_cached_csvs(
                project_id, BleachingQCProjectMethodObsQuadratBenthicPercentView, skip_updates
            )
            _update_cached_csvs(project_id, BleachingQCProjectMethodSUView, skip_updates)
            _update_cached_csvs(project_id, BleachingQCProjectMethodSEView, skip_updates)

        if sample_unit is None or sample_unit == HABITATCOMPLEXITY_PROTOCOL:
            _update_cached_csvs(project_id, HabitatComplexityProjectMethodObsView, skip_updates)
            _update_cached_csvs(project_id, HabitatComplexityProjectMethodSUView, skip_updates)
            _update_cached_csvs(project_id, HabitatComplexityProjectMethodSEView, skip_updates)

        _update_cached_csvs(project_id, SummarySampleEventView, skip_updates)

    except Exception as e:
        logger.error(f"Failed to update summary CSV cache for project {project_id}: {e}")
        raise UpdateSummariesException(message=str(e)) from e
