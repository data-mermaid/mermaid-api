from api.models import (
    CollectRecord,
    FishSpecies,
    Management,
    Project,
    RecordRevision,
    TableRevision,
)


def test_create_record_with_project_id(db_setup, project1, profile1):
    collect_record = CollectRecord.objects.create(
        project=project1, profile=profile1, data=dict()
    )

    rev_recs = RecordRevision.objects.filter(record_id=collect_record.id)
    assert rev_recs.count() == 1
    tabl_rev_rec = TableRevision.objects.get(
        table_name=CollectRecord._meta.db_table, project_id=project1.id
    )
    assert tabl_rev_rec.last_rev_id == rev_recs[0].rev_id


def test_create_project_record(db_setup):
    project = Project.objects.create(name="Revision Test", status=Project.TEST)
    rev_recs = RecordRevision.objects.filter(record_id=project.id)
    assert rev_recs.count() == 1
    tabl_rev_rec = TableRevision.objects.get(table_name=Project._meta.db_table)
    assert tabl_rev_rec.last_rev_id == rev_recs[0].rev_id


def test_create_non_project_record(db_setup, fish_genus1):
    fish = FishSpecies.objects.create(name="My Fish", genus=fish_genus1)
    rev_recs = RecordRevision.objects.filter(record_id=fish.id)
    assert rev_recs.count() == 1
    table_rev_rec = TableRevision.objects.get(table_name=FishSpecies._meta.db_table)
    assert table_rev_rec.last_rev_id == rev_recs[0].rev_id


def test_update_record(db_setup, project1):
    management = Management.objects.create(
        project=project1,
        est_year=2000,
        name="Management 2",
        notes="Hey what's up, from management2!!",
    )

    rev_recs = RecordRevision.objects.filter(record_id=management.id)
    rev_ids = [rr.rev_id for rr in rev_recs]

    tr = TableRevision.objects.get(
        table_name=Management._meta.db_table, project_id=project1.id
    )
    assert tr.last_rev_id in rev_ids
    assert rev_recs.count() == 1

    management.notes += "...some more notes"
    management.save()

    rev_recs = RecordRevision.objects.filter(record_id=management.id)
    rev_ids_updates = [rr.rev_id for rr in rev_recs]

    last_rev_id = list(set(rev_ids_updates).difference(set(rev_ids)))[0]

    qry = TableRevision.objects.filter(
        table_name=Management._meta.db_table,
        project_id=project1.id,
        last_rev_id=last_rev_id,
    )
    assert qry.count() == 1


def test_delete_record(db_setup, project1, profile1):
    collect_record = CollectRecord.objects.create(
        project=project1, profile=profile1, data=dict()
    )
    pk = collect_record.id
    qry = RecordRevision.objects.filter(record_id=pk, deleted=True)
    assert qry.count() == 0

    collect_record.delete()

    qry = RecordRevision.objects.filter(record_id=pk, deleted=True)

    assert qry.count() == 1


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
    
    rev_recs = RecordRevision.objects.filter(record_id=management_id)
    assert rev_recs.count() == 1
    assert rev_recs[0].deleted is False

    rev_recs = RecordRevision.objects.filter(record_id=management_id)
    management.delete()
    assert rev_recs.count() == 1
    assert rev_recs[0].deleted is True
