import pytest

from api.models import BenthicTransect


@pytest.fixture
def benthic_transect1(
    db, sample_event1, current1, reef_slope1, relative_depth1, tide1, visibility1,
):
    return BenthicTransect.objects.create(
        sample_event=sample_event1,
        current=current1,
        reef_slope=reef_slope1,
        relative_depth=relative_depth1,
        tide=tide1,
        visibility=visibility1,
        depth=5,
        len_surveyed=50,
        sample_time="11:00:00",
    )


@pytest.fixture
def benthic_transect2(
    db, sample_event2, current2, reef_slope2, relative_depth2, tide2, visibility2
):
    return BenthicTransect.objects.create(
        sample_event=sample_event2,
        current=current2,
        reef_slope=reef_slope2,
        relative_depth=relative_depth2,
        tide=tide2,
        visibility=visibility2,
        depth=2,
        len_surveyed=10,
        sample_time="10:00:00",
    )
