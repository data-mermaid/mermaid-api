from django.db.models.fields.related import ForeignKey
from api.models import *
from api.utils.timer import Timer

## TODO: Need to sort out grabbing subclass name (example: Observer.transectmethod)



def name(func):
    def _name(*args, **kwargs):
        func(*args, **kwargs)
        print(func.__name__)
    return _name


def get_model_value(model, lookups):
    lookup = lookups.pop(0)
    
    if type(model).__name__  == "RelatedManager":
        return None

    obj = getattr(model, lookup)
    if len(lookups) > 0:
        return get_model_value(obj, lookups)

    return obj


def get_related_project(model):

    if isinstance(model, Project):
        return model

    if hasattr(model, "project_lookup"):
        project_lookup = getattr(model, "project_lookup")
        lookups = project_lookup.split("__")
        rel_obj = get_model_value(model, lookups)
        if rel_obj:
            print(f"rel_obj: {rel_obj}")
            return rel_obj
    print(f"model: {model} {type(model)}")
    for f in model._meta.get_fields():
        if isinstance(f, ForeignKey):
            rel_obj = getattr(model, f.name)
            if rel_obj is not None:
                if isinstance(rel_obj, Project):
                    return rel_obj
                rel_obj = get_related_project(rel_obj)
                if rel_obj:
                    return rel_obj
    return None

@name
def test_site():
    model_instance = Site.objects.last()
    project_id = model_instance.project_id
    rel_model = get_related_project(model_instance)
    assert rel_model.pk == project_id

@name
def test_obs_belt_fish():
    model_instance = ObsBeltFish.objects.last()
    project_id = model_instance.beltfish.transect.sample_event.site.project_id
    rel_model = get_related_project(model_instance)
    assert rel_model.pk == project_id

@name
def test_project_profile():
    model_instance = ProjectProfile.objects.last()
    project_id = model_instance.project_id
    rel_model = get_related_project(model_instance)
    assert rel_model.pk == project_id

@name
def test_reef_slope():
    model_instance = ReefSlope.objects.last()
    rel_model = get_related_project(model_instance)
    assert rel_model is None

@name
def test_project():
    model_instance = Project.objects.last()
    rel_model = get_related_project(model_instance)
    assert model_instance.pk == rel_model.pk

@name
def test_sample_event():
    model_instance = SampleEvent.objects.last()
    project_id = model_instance.site.project_id
    rel_model = get_related_project(model_instance)
    assert project_id == rel_model.pk


@name
def test_quadrat_collection():
    model_instance = QuadratCollection.objects.last()
    project_id = model_instance.sample_event.site.project_id
    rel_model = get_related_project(model_instance)
    assert project_id == rel_model.pk


@name
def test_observer():
    model_instance = Observer.objects.last()
    project_id = model_instance.transectmethod.subclass.transect.sample_event.site.project_id
    rel_model = get_related_project(model_instance)

    # print(f"project_id: {project_id}")
    # print(f"rel_model.pk: {rel_model.pk}")
    # print(Project.objects.get(id=project_id))
    # print(Project.objects.get(id=rel_model.pk))
    assert project_id == rel_model.pk

def run():
    # test_site()
    # test_obs_belt_fish()
    # test_project_profile()
    # test_reef_slope()
    # test_project()
    # test_sample_event()
    # test_quadrat_collection()
    test_observer()

    print("..pass..")


    # model_instance = Site.objects.last()
    # # model_instance = ObsBeltFish.objects.last()
    # # model_instance = FishBeltTransect.objects.last()
    # project_id = model_instance.project_id
    # print(f"Project ID: {model_instance.project_id}")
    # # print(f"Project ID: {model_instance.beltfish.transect.sample_event.site.project_id}")
    # # print(f"model_instance: {model_instance}")
    
    # with Timer("Test Run"):
    #     rel_model = get_related_project(model_instance)
    
    # print(f"rel_model [{rel_model.pk}]: {rel_model}")
    # # rel_models = find_project_id(model_instance)
    # # for rm in rel_models:
    # #     print(f"\t{rm} {type(rm)}")