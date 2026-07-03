from django.conf import settings
from django.test import override_settings

from api.models import Classifier, CollectRecord


def test_setting_default_is_25():
    assert settings.INFERENCE_DEFAULT_NUM_POINTS == 25


@override_settings(INFERENCE_DEFAULT_NUM_POINTS=37)
def test_assign_classifier_signal_seeds_num_points_from_setting(project1, profile1):
    # At this task the Classifier model still has the num_points column (dropped in
    # Task 3). Give the classifier a num_points that DIFFERS from the setting so the
    # test proves the seeded value comes from the setting, not the classifier column.
    Classifier.objects.create(name="c", version="v-seed", patch_size=128, num_points=99)

    cr = CollectRecord.objects.create(
        project=project1,
        profile=profile1,
        data={
            "image_classification": True,
            "protocol": "benthicpqt",
            "quadrat_transect": {"num_quadrats": 1},
        },
    )

    assert cr.data["quadrat_transect"]["num_points_per_quadrat"] == 37
