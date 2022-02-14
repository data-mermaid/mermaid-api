from api.models import (
    ObsBeltFish,
    Observer,
    Project,
    ProjectProfile,
    QuadratCollection,
    ReefSlope,
    SampleEvent,
    Site,
)
from api.utils.related import get_related_project


def test_site(belt_fish_project):
    model_instance = Site.objects.last()
    project_id = model_instance.project_id
    rel_model = get_related_project(model_instance)
    assert rel_model.pk == project_id


def test_obs_belt_fish(belt_fish_project):
    model_instance = ObsBeltFish.objects.last()
    project_id = model_instance.beltfish.transect.sample_event.site.project_id
    rel_model = get_related_project(model_instance)
    assert rel_model.pk == project_id


def test_project_profile(belt_fish_project):
    model_instance = ProjectProfile.objects.last()
    project_id = model_instance.project_id
    rel_model = get_related_project(model_instance)
    assert rel_model.pk == project_id


def test_reef_slope(belt_fish_project):
    model_instance = ReefSlope.objects.last()
    rel_model = get_related_project(model_instance)
    assert rel_model is None


def test_project(belt_fish_project):
    model_instance = Project.objects.last()
    rel_model = get_related_project(model_instance)
    assert model_instance.pk == rel_model.pk


def test_sample_event(belt_fish_project):
    model_instance = SampleEvent.objects.last()
    project_id = model_instance.site.project_id
    rel_model = get_related_project(model_instance)
    assert project_id == rel_model.pk


def test_quadrat_collection(bleaching_project):
    model_instance = QuadratCollection.objects.last()
    project_id = model_instance.sample_event.site.project_id
    rel_model = get_related_project(model_instance)
    assert project_id == rel_model.pk


def test_observer(belt_fish_project, bleaching_project):
    model_instance = Observer.objects.last()
    project_id = (
        model_instance.transectmethod.subclass.transect.sample_event.site.project_id
    )
    rel_model = get_related_project(model_instance)

    assert project_id == rel_model.pk
