from .base import FishAttributeView, SampleEventViewModel
from .beltfish import BeltFishObsView, BeltFishSEView, BeltFishSUView
from .benthiclit import BenthicLITObsView, BenthicLITSEView, BenthicLITSUView
from .benthicpit import BenthicPITObsView, BenthicPITSEView, BenthicPITSUView
from .bleachingqc import (
    BleachingQCColoniesBleachedObsView,
    BleachingQCQuadratBenthicPercentObsView,
    BleachingQCSEView,
    BleachingQCSUView,
)
from .habitatcomplexity import (
    HabitatComplexityObsView,
    HabitatComplexitySEView,
    HabitatComplexitySUView,
)
from api.models.sql_models.summary_site import SummarySiteViewModel


def forward_sql():
    sql = [
        FishAttributeView.sql,
        SampleEventViewModel.sql,
        BeltFishObsView.sql,
        BeltFishSUView.sql,
        BeltFishSEView.sql,
        BenthicPITObsView.sql,
        BenthicPITSUView.sql,
        BenthicPITSEView.sql,
        BenthicLITObsView.sql,
        BenthicLITSUView.sql,
        BenthicLITSEView.sql,
        BleachingQCColoniesBleachedObsView.sql,
        BleachingQCQuadratBenthicPercentObsView.sql,
        BleachingQCSUView.sql,
        BleachingQCSEView.sql,
        HabitatComplexityObsView.sql,
        HabitatComplexitySUView.sql,
        HabitatComplexitySEView.sql,
        SummarySiteViewModel.sql,
    ]
    output = []
    for s in sql:
        s = s.strip()
        if s[-1] != ";":
            s += ";"

        output.append(s)

    return reverse_sql() + "\n".join(output)


def reverse_sql():
    sql = [
        SummarySiteViewModel.reverse_sql,
        BeltFishSEView.reverse_sql,
        BeltFishSUView.reverse_sql,
        BeltFishObsView.reverse_sql,
        BenthicPITSEView.reverse_sql,
        BenthicPITSUView.reverse_sql,
        BenthicPITObsView.reverse_sql,
        BenthicLITSEView.reverse_sql,
        BenthicLITSUView.reverse_sql,
        BenthicLITObsView.reverse_sql,
        BleachingQCSEView.reverse_sql,
        BleachingQCSUView.reverse_sql,
        BleachingQCQuadratBenthicPercentObsView.reverse_sql,
        BleachingQCColoniesBleachedObsView.reverse_sql,
        HabitatComplexitySEView.reverse_sql,
        HabitatComplexitySUView.reverse_sql,
        HabitatComplexityObsView.reverse_sql,
        SampleEventViewModel.reverse_sql,
        FishAttributeView.reverse_sql,
    ]

    output = []
    for s in sql:
        s = s.strip()
        if s[-1] != ";":
            s += ";"

        output.append(s)

    return "\n".join(output)
