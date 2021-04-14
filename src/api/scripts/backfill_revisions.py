
import datetime
from django.db import connection
from api.models import CollectRecord, Management, Site, ProjectProfile, Project, FishSpecies



def _backfill_collect_record():
    with connection.cursor() as cur:
        ts = datetime.datetime.now()
        for cr in CollectRecord.objects.all():
            sql = f"""
                INSERT into record_revision(
                    "table_name",
                    "record_id",
                    "project_id",
                    "profile_id",
                    "updated_on",
                    "deleted"
                )
                VALUES (
                    'api_collectrecord',
                    '{cr.id}'::uuid,
                    '{cr.project_id}'::uuid,
                    '{cr.profile_id}'::uuid,
                    '{ts}'::timestamp,
                    false
                )
            """
            cur.execute(sql)

def _backfill_site():
    with connection.cursor() as cur:
        ts = datetime.datetime.now()
        for cr in Site.objects.all():
            sql = f"""
                INSERT into record_revision(
                    "table_name",
                    "record_id",
                    "project_id",
                    "profile_id",
                    "updated_on",
                    "deleted"
                )
                VALUES (
                    'site',
                    '{cr.id}'::uuid,
                    '{cr.project_id}'::uuid,
                    null,
                    '{ts}'::timestamp,
                    false
                )
            """
            cur.execute(sql)


def _backfill_management():
    with connection.cursor() as cur:
        ts = datetime.datetime.now()
        for cr in Management.objects.all():
            sql = f"""
                INSERT into record_revision(
                    "table_name",
                    "record_id",
                    "project_id",
                    "profile_id",
                    "updated_on",
                    "deleted"
                )
                VALUES (
                    'management',
                    '{cr.id}'::uuid,
                    '{cr.project_id}'::uuid,
                    null,
                    '{ts}'::timestamp,
                    false
                )
            """
            cur.execute(sql)
        
def run():
    _backfill_collect_record()
    _backfill_management()
    _backfill_site()