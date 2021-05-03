import uuid

from django.contrib.gis.db import models


class Revision(models.Model):
    table_name = models.CharField(max_length=50, db_index=True, editable=False)
    record_id = models.UUIDField(db_index=True, editable=False)
    project_id = models.UUIDField(null=True, db_index=True, editable=False)
    profile_id = models.UUIDField(null=True, db_index=True, editable=False)
    revision_num = models.IntegerField(null=False, default=1)
    updated_on = models.DateTimeField(editable=False)
    deleted = models.BooleanField(default=False, editable=False)

    class Meta:
        db_table = "revision"
        unique_together = ("table_name", "record_id")

    def __str__(self):
        return f"[{self.revision_num}] {self.table_name} {self.record_id}"


# -- TRIGGER SQL --

forward_sql = """
    CREATE SEQUENCE revision_seq_num START 1;
    SELECT setval('revision_seq_num', (SELECT MAX(revision_num) FROM revision));

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
        ON CONFLICT (table_name, record_id) DO
        UPDATE SET
            "revision_num" = rev_num,
            "updated_on" = updated_on_val,
            "project_id" = project_id_val,
            "profile_id" = profile_id_val,
            "deleted" = is_deleted;

        RETURN NULL;

    END;
    $$;

    CREATE TRIGGER fish_species_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "fish_species" FOR EACH ROW EXECUTE FUNCTION write_revision();

    CREATE TRIGGER management_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "management" FOR EACH ROW EXECUTE FUNCTION write_revision();

    CREATE TRIGGER api_collectrecord_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "api_collectrecord" FOR EACH ROW EXECUTE FUNCTION write_revision();

    CREATE TRIGGER benthic_attribute_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "benthic_attribute" FOR EACH ROW EXECUTE FUNCTION write_revision();

    CREATE TRIGGER fish_genus_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "fish_genus" FOR EACH ROW EXECUTE FUNCTION write_revision();

    CREATE TRIGGER fish_family_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "fish_family" FOR EACH ROW EXECUTE FUNCTION write_revision();

    CREATE TRIGGER site_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "site" FOR EACH ROW EXECUTE FUNCTION write_revision();

    CREATE TRIGGER project_profile_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "project_profile" FOR EACH ROW EXECUTE FUNCTION write_revision();

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
    DROP TRIGGER site_trigger ON site;    
    DROP TRIGGER project_profile_trigger ON project_profile;
    DROP TRIGGER project_trigger ON project;

    DROP FUNCTION write_revision;
    DROP FUNCTION primary_key_column_name(text);
    DROP SEQUENCE revision_seq_num;
"""

# -//- TRIGGER SQL -//-
