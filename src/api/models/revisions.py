from django.contrib.gis.db import models
from django.db import connection
from django.utils import timezone

from .base import ExtendedManager, ExtendedQuerySet


class Revision(models.Model):
    table_name = models.CharField(max_length=50, db_index=True, editable=False)
    record_id = models.UUIDField(db_index=True, editable=False)
    project_id = models.UUIDField(null=True, db_index=True, editable=False)
    profile_id = models.UUIDField(null=True, db_index=True, editable=False)
    revision_num = models.IntegerField(null=False, default=1)
    updated_on = models.DateTimeField(editable=False)
    deleted = models.BooleanField(default=False, editable=False)
    related_to_profile_id = models.UUIDField(null=True, db_index=True, editable=False)

    objects = ExtendedManager.from_queryset(ExtendedQuerySet)()

    class Meta:
        db_table = "revision"
        constraints = [
            models.UniqueConstraint(
                fields=["table_name", "record_id", "related_to_profile_id"],
                name="unique_revision_table_record_profile"
            )
        ]

    def __str__(self):
        return f"[{self.revision_num}] {self.table_name} {self.record_id}"

    def __lt__(self, other):
        return self.revision_num < other.revision_num

    def __le__(self, other):
        return self.revision_num <= other.revision_num

    def __gt__(self, other):
        return self.revision_num > other.revision_num

    def __ge__(self, other):
        return self.revision_num >= other.revision_num

    def __eq__(self, other):
        return self.revision_num == other.revision_num

    @classmethod
    def create(
        cls,
        table_name,
        record_id,
        project_id=None,
        profile_id=None,
        deleted=False,
        related_to_profile_id=None,
    ):
        cursor = connection.cursor()
        try:
            timestamp = timezone.now()
            sql = "SELECT nextval('revision_seq_num');"
            cursor.execute(sql)
            revision_num = cursor.fetchone()[0]

            if related_to_profile_id is None:
                upsert_sql = """
                    INSERT INTO revision (
                        "table_name",
                        "record_id",
                        "project_id",
                        "profile_id",
                        "revision_num",
                        "updated_on",
                        "deleted",
                        "related_to_profile_id"
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (table_name, record_id)
                    WHERE related_to_profile_id IS NULL
                    DO UPDATE SET
                        -- Use GREATEST to ensure revision_num and updated_on only ever increase
                        -- in the case of concurrent updates.
                        "revision_num" = GREATEST(revision.revision_num, EXCLUDED.revision_num),
                        "updated_on" = GREATEST(revision.updated_on, EXCLUDED.updated_on),
                        -- Only update metadata columns if incoming revision is newer
                        "project_id" = CASE
                            WHEN EXCLUDED.revision_num > revision.revision_num THEN EXCLUDED.project_id
                            WHEN EXCLUDED.revision_num = revision.revision_num AND EXCLUDED.updated_on > revision.updated_on THEN EXCLUDED.project_id
                            ELSE revision.project_id
                        END,
                        "profile_id" = CASE
                            WHEN EXCLUDED.revision_num > revision.revision_num THEN EXCLUDED.profile_id
                            WHEN EXCLUDED.revision_num = revision.revision_num AND EXCLUDED.updated_on > revision.updated_on THEN EXCLUDED.profile_id
                            ELSE revision.profile_id
                        END,
                        "deleted" = CASE
                            WHEN EXCLUDED.revision_num > revision.revision_num THEN EXCLUDED.deleted
                            WHEN EXCLUDED.revision_num = revision.revision_num AND EXCLUDED.updated_on > revision.updated_on THEN EXCLUDED.deleted
                            ELSE revision.deleted
                        END
                    RETURNING id;
                """
            else:
                upsert_sql = """
                    INSERT INTO revision (
                        "table_name",
                        "record_id",
                        "project_id",
                        "profile_id",
                        "revision_num",
                        "updated_on",
                        "deleted",
                        "related_to_profile_id"
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (table_name, record_id, related_to_profile_id)
                    DO UPDATE SET
                        "revision_num" = GREATEST(revision.revision_num, EXCLUDED.revision_num),
                        "updated_on" = GREATEST(revision.updated_on, EXCLUDED.updated_on),
                        -- Only update metadata columns if incoming revision is newer
                        "project_id" = CASE
                            WHEN EXCLUDED.revision_num > revision.revision_num THEN EXCLUDED.project_id
                            WHEN EXCLUDED.revision_num = revision.revision_num AND EXCLUDED.updated_on > revision.updated_on THEN EXCLUDED.project_id
                            ELSE revision.project_id
                        END,
                        "profile_id" = CASE
                            WHEN EXCLUDED.revision_num > revision.revision_num THEN EXCLUDED.profile_id
                            WHEN EXCLUDED.revision_num = revision.revision_num AND EXCLUDED.updated_on > revision.updated_on THEN EXCLUDED.profile_id
                            ELSE revision.profile_id
                        END,
                        "deleted" = CASE
                            WHEN EXCLUDED.revision_num > revision.revision_num THEN EXCLUDED.deleted
                            WHEN EXCLUDED.revision_num = revision.revision_num AND EXCLUDED.updated_on > revision.updated_on THEN EXCLUDED.deleted
                            ELSE revision.deleted
                        END
                    RETURNING id;
                """

            cursor.execute(
                upsert_sql,
                [
                    table_name,
                    record_id,
                    project_id,
                    profile_id,
                    revision_num,
                    timestamp,
                    deleted,
                    related_to_profile_id,
                ],
            )

            revision_id = cursor.fetchone()[0]
            return Revision.objects.get(id=revision_id)

        finally:
            if cursor:
                cursor.close()

    @classmethod
    def _get_project_id(cls, instance):
        if hasattr(instance, "project_id"):
            return instance.project_id

        if hasattr(instance, "project_lookup"):
            project_lookup = instance.project_lookup
            attrs = project_lookup.split("__")
            val = getattr(instance, attrs.pop(0))
            for attr in attrs:
                val = getattr(val, attr)

            if val:
                return val.pk

        return None

    @classmethod
    def create_from_instance(
        cls, instance, profile_id=None, deleted=False, related_to_profile_id=None
    ):
        table_name = instance._meta.db_table
        record_id = instance.pk
        project_id = cls._get_project_id(instance)

        return cls.create(
            table_name, record_id, project_id, profile_id, deleted, related_to_profile_id
        )

    @classmethod
    def remove(
        cls,
        table_name,
        record_id,
        project_id=None,
        profile_id=None,
        deleted=False,
        related_to_profile_id=None,
    ):
        Revision.objects.filter(
            table_name=table_name,
            record_id=record_id,
            project_id=project_id,
            profile_id=profile_id,
            deleted=deleted,
            related_to_profile_id=related_to_profile_id,
        ).delete()

    @classmethod
    def remove_from_instance(
        cls, instance, profile_id=None, deleted=False, related_to_profile_id=None
    ):
        table_name = instance._meta.db_table
        record_id = instance.pk
        project_id = cls._get_project_id(instance)

        return cls.remove(
            table_name, record_id, project_id, profile_id, deleted, related_to_profile_id
        )


# -- TRIGGER SQL --

forward_sql = """
    -- This index is needed to allow upsert to catch null values with related_to_profile_id
    -- (a.k.a. make the ON CONFLICT work)
    -- Reference: https://dba.stackexchange.com/questions/151431/postgresql-upsert-issue-with-null-values/151438#151438

    CREATE UNIQUE INDEX IF NOT EXISTS revision_related_to_profile_id_upsert_idx
    ON public.revision (table_name, record_id)
    WHERE revision.related_to_profile_id IS NULL;

    CREATE SEQUENCE IF NOT EXISTS revision_seq_num START 1;

    CREATE OR REPLACE FUNCTION primary_key_column_name (table_name text)
    RETURNS varchar AS $$
    DECLARE
    column_name text;
    BEGIN
        SELECT
            pg_attribute.attname
        INTO
            column_name
        FROM pg_index, pg_class, pg_attribute, pg_namespace
        WHERE
            pg_class.oid = table_name::regclass AND
            indrelid = pg_class.oid AND
            nspname = 'public' AND
            pg_class.relnamespace = pg_namespace.oid AND
            pg_attribute.attrelid = pg_class.oid AND
            pg_attribute.attnum = any(pg_index.indkey)
            AND indisprimary;
        RETURN column_name;

    END;
    $$
    LANGUAGE plpgsql;

    CREATE OR REPLACE FUNCTION write_revision()
    RETURNS TRIGGER LANGUAGE PLPGSQL AS $$

    DECLARE
        pk uuid;
        revision_id int;
        profile_id_val uuid;
        project_id_val uuid;
        is_deleted boolean;
        updated_on_val timestamp;
        pk_col_name varchar;
        record jsonb;
        rev_num bigint;

    BEGIN
        rev_num := nextval('revision_seq_num');
        pk_col_name := primary_key_column_name(TG_TABLE_NAME);
        updated_on_val := now();

        IF TG_OP = 'DELETE' THEN
            record := to_jsonb(OLD);
            is_deleted := true;
        ELSE
            record := to_jsonb(NEW);
            is_deleted := false;
        END IF;

        pk := record->>pk_col_name;

        IF record ? 'profile_id' THEN
            profile_id_val := record->>'profile_id';
        ELSE
            profile_id_val := null;
        END IF;

        IF record ? 'project_id' THEN
            project_id_val := record->>'project_id';
        ELSIF TG_TABLE_NAME = 'project' THEN
            project_id_val := pk;
        ELSE
            project_id_val := null;
        END IF;

        INSERT INTO revision (
            "table_name",
            "record_id",
            "project_id",
            "profile_id",
            "revision_num",
            "updated_on",
            "deleted"
        )
        VALUES (
            TG_TABLE_NAME,
            pk,
            project_id_val,
            profile_id_val,
            rev_num,
            updated_on_val,
            is_deleted
        )
        ON CONFLICT (table_name, record_id)
        WHERE related_to_profile_id IS NULL
        DO UPDATE SET
            "revision_num" = GREATEST(revision.revision_num, rev_num),
            "updated_on" = GREATEST(revision.updated_on, updated_on_val),
            -- Only update metadata columns if incoming revision is newer
            "project_id" = CASE
                WHEN rev_num > revision.revision_num THEN project_id_val
                WHEN rev_num = revision.revision_num AND updated_on_val > revision.updated_on THEN project_id_val
                ELSE revision.project_id
            END,
            "profile_id" = CASE
                WHEN rev_num > revision.revision_num THEN profile_id_val
                WHEN rev_num = revision.revision_num AND updated_on_val > revision.updated_on THEN profile_id_val
                ELSE revision.profile_id
            END,
            "deleted" = CASE
                WHEN rev_num > revision.revision_num THEN is_deleted
                WHEN rev_num = revision.revision_num AND updated_on_val > revision.updated_on THEN is_deleted
                ELSE revision.deleted
            END;

        RETURN NULL;

    END;
    $$;

    DROP TRIGGER IF EXISTS fish_species_trigger ON "fish_species";
    CREATE TRIGGER fish_species_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "fish_species" FOR EACH ROW EXECUTE FUNCTION write_revision();

    DROP TRIGGER IF EXISTS management_trigger ON management;
    CREATE TRIGGER management_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "management" FOR EACH ROW EXECUTE FUNCTION write_revision();

    DROP TRIGGER IF EXISTS api_collectrecord_trigger ON api_collectrecord;
    CREATE TRIGGER api_collectrecord_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "api_collectrecord" FOR EACH ROW EXECUTE FUNCTION write_revision();

    DROP TRIGGER IF EXISTS benthic_attribute_trigger ON benthic_attribute;
    CREATE TRIGGER benthic_attribute_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "benthic_attribute" FOR EACH ROW EXECUTE FUNCTION write_revision();

    DROP TRIGGER IF EXISTS fish_genus_trigger ON fish_genus;
    CREATE TRIGGER fish_genus_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "fish_genus" FOR EACH ROW EXECUTE FUNCTION write_revision();

    DROP TRIGGER IF EXISTS fish_family_trigger ON fish_family;
    CREATE TRIGGER fish_family_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "fish_family" FOR EACH ROW EXECUTE FUNCTION write_revision();

    DROP TRIGGER IF EXISTS fish_grouping_trigger ON fish_grouping;
    CREATE TRIGGER fish_grouping_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "fish_grouping" FOR EACH ROW EXECUTE FUNCTION write_revision();

    DROP TRIGGER IF EXISTS site_trigger ON site;
    CREATE TRIGGER site_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "site" FOR EACH ROW EXECUTE FUNCTION write_revision();

    DROP TRIGGER IF EXISTS project_profile_trigger ON project_profile;
    CREATE TRIGGER project_profile_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "project_profile" FOR EACH ROW EXECUTE FUNCTION write_revision();

    DROP TRIGGER IF EXISTS project_trigger ON project;
    CREATE TRIGGER project_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "project" FOR EACH ROW EXECUTE FUNCTION write_revision();
"""

reverse_sql = """
    DROP TRIGGER fish_species_trigger ON fish_species;
    DROP TRIGGER management_trigger ON management;
    DROP TRIGGER api_collectrecord_trigger ON api_collectrecord;
    DROP TRIGGER benthic_attribute_trigger ON benthic_attribute;
    DROP TRIGGER fish_genus_trigger ON fish_genus;
    DROP TRIGGER fish_family_trigger ON fish_family;
    DROP TRIGGER fish_grouping_trigger ON fish_grouping;
    DROP TRIGGER site_trigger ON site;
    DROP TRIGGER project_profile_trigger ON project_profile;
    DROP TRIGGER project_trigger ON project;

    DROP FUNCTION write_revision;
    DROP FUNCTION primary_key_column_name(text);
    DROP SEQUENCE revision_seq_num;
"""

# -//- TRIGGER SQL -//-
