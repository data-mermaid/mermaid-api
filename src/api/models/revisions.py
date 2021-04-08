import uuid

from django.contrib.gis.db import models


class RecordRevision(models.Model):
    rev_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    table_name = models.CharField(max_length=50, db_index=True)
    record_id = models.UUIDField(db_index=True)
    project_id = models.UUIDField(null=True, blank=True, db_index=True)
    profile_id = models.UUIDField(null=True, blank=True)
    updated_on = models.DateTimeField(auto_now=True)
    deleted = models.BooleanField(default=False)

    class Meta:
        db_table = "record_revision"

    def __str__(self):
        return f"[{self.rev_id} {self.updated_on}] {self.table_name} {self.record_id}"


class TableRevision(models.Model):
    last_rev_id = models.UUIDField(db_index=True)
    table_name = models.CharField(max_length=50, db_index=True)
    updated_on = models.DateTimeField()
    project_id = models.UUIDField(null=True, blank=True, db_index=True)

    class Meta:
        db_table = "table_revision"
        unique_together = ("table_name", "project_id")

    def __str__(self):
        return f"[{self.last_rev_id}] {self.table_name} - {self.updated_on}"


# -- TRIGGER SQL --

forward_sql = """
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

    CREATE OR REPLACE FUNCTION record_change()
    RETURNS TRIGGER LANGUAGE PLPGSQL AS $$

    DECLARE
        pk uuid;
        rev_id_val uuid;
        profile_id_val uuid;
        project_id_val uuid;
        is_deleted boolean;
        updated_on_val timestamp;
        pk_col_name varchar;
        record jsonb;

    BEGIN
        pk_col_name := primary_key_column_name(TG_TABLE_NAME);
        updated_on_val := now();
        rev_id_val := uuid_generate_v4();

        IF TG_OP = 'DELETE' THEN
            record := to_jsonb(OLD);
            is_deleted := true;
        ELSE
            record := to_jsonb(NEW);
            is_deleted := false;
        END IF;

        pk := record->>pk_col_name;

        IF record ? 'profile_id' THEN
            profile_id_val := NEW.profile_id;
        ELSE
            profile_id_val := null;
        END IF;

        IF record ? 'project_id' THEN
            project_id_val := NEW.project_id;
        ELSE
            project_id_val := null;
        END IF;

        INSERT INTO record_revision (
            "rev_id",
            "table_name",
            "record_id",
            "project_id",
            "profile_id",
            "updated_on",
            "deleted"
        )
        VALUES (
            rev_id_val,
            TG_TABLE_NAME,
            pk,
            project_id_val,
            profile_id_val,
            updated_on_val,
            is_deleted
        );

        INSERT INTO table_revision(
            "last_rev_id",
            "table_name",
            "updated_on",
            "project_id"
        )
        VALUES (
            rev_id_val,
            TG_TABLE_NAME,
            updated_on_val,
            Case WHEN project_id_val is null THEN
                '00000000-0000-0000-0000-000000000000'::uuid
            ELSE project_id_val END
        )
        ON CONFLICT (table_name, project_id) DO
        UPDATE SET
            "last_rev_id" = rev_id_val,
            "updated_on" = updated_on_val;
        RETURN NULL;

    END;
    $$;

    CREATE TRIGGER fish_species_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "fish_species" FOR EACH ROW EXECUTE FUNCTION record_change();

    CREATE TRIGGER management_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "management" FOR EACH ROW EXECUTE FUNCTION record_change();

    CREATE TRIGGER growth_form_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "growth_form" FOR EACH ROW EXECUTE FUNCTION record_change();

    CREATE TRIGGER api_collectrecord_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "api_collectrecord" FOR EACH ROW EXECUTE FUNCTION record_change();

    CREATE TRIGGER benthic_attribute_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "benthic_attribute" FOR EACH ROW EXECUTE FUNCTION record_change();

    /*
    CREATE TRIGGER fish_attribute_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "fish_attribute" FOR EACH ROW EXECUTE FUNCTION record_change();
    */
    CREATE TRIGGER fish_genus_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "fish_genus" FOR EACH ROW EXECUTE FUNCTION record_change();

    CREATE TRIGGER fish_family_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "fish_family" FOR EACH ROW EXECUTE FUNCTION record_change();

    CREATE TRIGGER api_fishsize_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "api_fishsize" FOR EACH ROW EXECUTE FUNCTION record_change();

    CREATE TRIGGER site_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "site" FOR EACH ROW EXECUTE FUNCTION record_change();

    CREATE TRIGGER region_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "region" FOR EACH ROW EXECUTE FUNCTION record_change();

    CREATE TRIGGER project_profile_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "project_profile" FOR EACH ROW EXECUTE FUNCTION record_change();

    CREATE TRIGGER project_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "project" FOR EACH ROW EXECUTE FUNCTION record_change();

    CREATE TRIGGER management_parties_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "management_parties" FOR EACH ROW EXECUTE FUNCTION record_change();

    CREATE TRIGGER country_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "country" FOR EACH ROW EXECUTE FUNCTION record_change();

    CREATE TRIGGER fish_group_function_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "fish_group_function" FOR EACH ROW EXECUTE FUNCTION record_change();

    CREATE TRIGGER fish_group_trophic_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "fish_group_trophic" FOR EACH ROW EXECUTE FUNCTION record_change();

    CREATE TRIGGER api_habitatcomplexityscore_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "api_habitatcomplexityscore"
        FOR EACH ROW EXECUTE FUNCTION record_change();

    CREATE TRIGGER api_belttransectwidth_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "api_belttransectwidth"
        FOR EACH ROW EXECUTE FUNCTION record_change();

    CREATE TRIGGER fish_group_size_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "fish_group_size"
        FOR EACH ROW EXECUTE FUNCTION record_change();

    CREATE TRIGGER api_reefzone_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "api_reefzone" FOR EACH ROW EXECUTE FUNCTION record_change();

    CREATE TRIGGER api_tide_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "api_tide" FOR EACH ROW EXECUTE FUNCTION record_change();

    CREATE TRIGGER benthic_lifehistory_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "benthic_lifehistory" FOR EACH ROW EXECUTE FUNCTION record_change();

    CREATE TRIGGER api_reefslope_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "api_reefslope" FOR EACH ROW EXECUTE FUNCTION record_change();

    CREATE TRIGGER api_reeftype_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "api_reeftype" FOR EACH ROW EXECUTE FUNCTION record_change();

    CREATE TRIGGER management_compliance_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "management_compliance" FOR EACH ROW EXECUTE FUNCTION record_change();

    CREATE TRIGGER management_party_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "management_party" FOR EACH ROW EXECUTE FUNCTION record_change();

    CREATE TRIGGER api_visibility_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "api_visibility" FOR EACH ROW EXECUTE FUNCTION record_change();

    CREATE TRIGGER api_reefexposure_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "api_reefexposure" FOR EACH ROW EXECUTE FUNCTION record_change();

    CREATE TRIGGER api_fishsizebin_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "api_fishsizebin" FOR EACH ROW EXECUTE FUNCTION record_change();

    CREATE TRIGGER api_current_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "api_current" FOR EACH ROW EXECUTE FUNCTION record_change();

    CREATE TRIGGER api_relativedepth_trigger
    AFTER
    INSERT
        OR
    UPDATE
        OR DELETE ON "api_relativedepth" FOR EACH ROW EXECUTE FUNCTION record_change();
"""

reverse_sql = """
    DROP TRIGGER fish_species_trigger ON fish_species;
    DROP TRIGGER management_trigger ON management;
    DROP TRIGGER growth_form_trigger ON growth_form;
    DROP TRIGGER api_collectrecord_trigger ON api_collectrecord;
    DROP TRIGGER benthic_attribute_trigger ON benthic_attribute;
    DROP TRIGGER fish_attribute_trigger ON fish_attribute;
    DROP TRIGGER fish_genus_trigger ON fish_genus;
    DROP TRIGGER fish_family_trigger ON fish_family;
    DROP TRIGGER api_fishsize_trigger ON api_fishsize;
    DROP TRIGGER site_trigger ON site;
    DROP TRIGGER region_trigger ON region;
    DROP TRIGGER project_profile_trigger ON project_profile;
    DROP TRIGGER project_trigger ON project;
    DROP TRIGGER management_parties_trigger ON management_parties;
    DROP TRIGGER country_trigger ON country;
    DROP TRIGGER fish_group_function_trigger ON fish_group_function;
    DROP TRIGGER fish_group_trophic_trigger ON fish_group_trophic;
    DROP TRIGGER api_habitatcomplexityscore_trigger ON api_habitatcomplexityscore;
    DROP TRIGGER api_belttransectwidth_trigger ON api_belttransectwidth;
    DROP TRIGGER fish_group_size_trigger ON fish_group_size;
    DROP TRIGGER api_reefzone_trigger ON api_reefzone;
    DROP TRIGGER api_tide_trigger ON api_tide;
    DROP TRIGGER benthic_lifehistory_trigger ON benthic_lifehistory;
    DROP TRIGGER api_reefslope_trigger ON api_reefslope;
    DROP TRIGGER api_reeftype_trigger ON api_reeftype;
    DROP TRIGGER management_compliance_trigger ON management_compliance;
    DROP TRIGGER management_party_trigger ON management_party;
    DROP TRIGGER api_visibility_trigger ON api_visibility;
    DROP TRIGGER api_reefexposure_trigger ON api_reefexposure;
    DROP TRIGGER api_fishsizebin_trigger ON api_fishsizebin;
    DROP TRIGGER api_current_trigger ON api_current;
    DROP TRIGGER api_relativedepth_trigger ON api_relativedepth;

    DROP FUNCTION record_change;
"""

# -//- TRIGGER SQL -//-
