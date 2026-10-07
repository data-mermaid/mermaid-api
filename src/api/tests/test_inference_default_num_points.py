from django.test import override_settings

from api.models import Classifier, CollectRecord


def _image_classification_record(project, profile):
    return CollectRecord.objects.create(
        project=project,
        profile=profile,
        data={
            "image_classification": True,
            "protocol": "benthicpqt",
            "quadrat_transect": {"num_quadrats": 1},
        },
    )


@override_settings(INFERENCE_DEFAULT_NUM_POINTS=37, INFERENCE_CLASSIFIER_VERSION="v-seed")
def test_assign_classifier_signal_seeds_num_points_from_setting(project1, profile1):
    # The Classifier model exposes no num_points, so nothing on the classifier can
    # supply num_points_per_quadrat and the seeded value can only come from the setting.
    Classifier.objects.create(name="c", version="v-seed", config={"patch_size": 128})

    cr = _image_classification_record(project1, profile1)

    assert cr.data["quadrat_transect"]["num_points_per_quadrat"] == 37


@override_settings(INFERENCE_CLASSIFIER_VERSION="v1")
def test_assign_classifier_signal_stamps_the_pinned_version_not_the_newest(project1, profile1):
    pinned = Classifier.objects.create(name="v1", version="v1", config={"patch_size": 128})
    Classifier.objects.create(name="v2", version="v2", config={"patch_size": 128})

    cr = _image_classification_record(project1, profile1)

    assert cr.data["classifier_id"] == str(pinned.pk)


@override_settings(INFERENCE_CLASSIFIER_VERSION="v-unregistered")
def test_assign_classifier_signal_skips_when_the_pin_has_no_row(project1, profile1):
    Classifier.objects.create(name="v2", version="v2", config={"patch_size": 128})

    cr = _image_classification_record(project1, profile1)

    assert "classifier_id" not in cr.data
    assert "num_points_per_quadrat" not in cr.data["quadrat_transect"]
