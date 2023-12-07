from api.models import CollectRecord, FishSpecies, Management, Project, Revision


def test_create_record_with_project_id(db_setup, project1, profile1):
    collect_record = CollectRecord.objects.create(project=project1, profile=profile1, data=dict())

    rev_recs = Revision.objects.filter(record_id=collect_record.id)
    assert rev_recs.count() == 1


def test_create_project_record(db_setup):
    project = Project.objects.create(name="Revision Test", status=Project.TEST)
    rev_recs = Revision.objects.filter(record_id=project.id)
    assert rev_recs.count() == 1


def test_create_non_project_record(db_setup, fish_genus1):
    fish = FishSpecies.objects.create(name="My Fish", genus=fish_genus1)
    rev_recs = Revision.objects.filter(record_id=fish.id)
    assert rev_recs.count() == 1


def test_create_update_delete_record(db_setup, project1):
    management = Management.objects.create(
        project=project1,
        est_year=2000,
        name="Management 2",
        notes="Hey what's up, from management2!!",
    )
    management_id = management.id
    management.notes = "a note"
    management.save()

    rev_recs = Revision.objects.filter(record_id=management_id)
    assert rev_recs.count() == 1
    assert rev_recs[0].deleted is False

    rev_recs = Revision.objects.filter(record_id=management_id)
    management.delete()
    assert rev_recs.count() == 1
    assert rev_recs[0].deleted is True
