import csv
import importlib
import json
import shutil
from datetime import date
from unittest import mock

import pytest
from django.db import connection
from django.db.migrations.loader import MigrationLoader
from django.test import override_settings

_migration_module = importlib.import_module("api.migrations.0135_export_covariates")
export_covariates = _migration_module.export_covariates


@pytest.fixture
def historical_apps():
    # Tests run with --no-migrations; load the real migration graph so this
    # keeps working once the live Covariate model is deleted.
    with override_settings(MIGRATION_MODULES={}):
        loader = MigrationLoader(connection, ignore_no_migrations=True)
        return loader.project_state(("api", "0135_export_covariates")).apps


@pytest.fixture
def covariate_model(historical_apps):
    Covariate = historical_apps.get_model("api", "Covariate")
    created = Covariate._meta.db_table not in connection.introspection.table_names()
    if created:
        with connection.schema_editor() as editor:
            editor.create_model(Covariate)
    yield Covariate
    if created:
        with connection.schema_editor() as editor:
            editor.delete_model(Covariate)


@pytest.fixture
def covariates(covariate_model, site1, site2):
    return [
        covariate_model.objects.create(
            site_id=site1.pk,
            name="aca_benthic",
            datestamp=date(2024, 1, 1),
            requested_datestamp=date(2024, 1, 2),
            value=[{"name": "Sand", "area": 0.5}],
            data={"a": 1},
        ),
        covariate_model.objects.create(
            site_id=site2.pk,
            name="beyer_score",
            datestamp=date(2024, 1, 1),
            requested_datestamp=date(2024, 1, 2),
            value=0.3,
        ),
    ]


def _run_export(historical_apps, environment, tmp_path):
    uploads = []

    def fake_upload(bucket, local_file_path, blob_name, content_type=None):
        shutil.copy(local_file_path, tmp_path / "export.csv")
        uploads.append((bucket, blob_name, content_type))

    with (
        mock.patch.object(_migration_module.s3, "upload_file", side_effect=fake_upload),
        mock.patch.object(_migration_module.settings, "ENVIRONMENT", environment),
    ):
        export_covariates(historical_apps, None)
    return uploads


def test_export_covariates_uploads_all_rows(db_setup, historical_apps, covariates, tmp_path):
    uploads = _run_export(historical_apps, "dev", tmp_path)

    assert len(uploads) == 1
    bucket, blob_name, content_type = uploads[0]
    assert blob_name.startswith("dev/covariate_export/covariates_")
    assert content_type == "text/csv"

    with open(tmp_path / "export.csv", newline="") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 2
    assert list(rows[0].keys()) == _migration_module.EXPORT_FIELDS
    by_name = {r["name"]: r for r in rows}
    assert by_name["aca_benthic"]["site_id"] == str(covariates[0].site_id)
    assert json.loads(by_name["aca_benthic"]["value"]) == [{"name": "Sand", "area": 0.5}]
    assert json.loads(by_name["aca_benthic"]["data"]) == {"a": 1}
    assert json.loads(by_name["beyer_score"]["value"]) == 0.3
    assert json.loads(by_name["beyer_score"]["data"]) is None
    assert by_name["beyer_score"]["created_on"]


def test_export_covariates_skips_local(db_setup, historical_apps, covariates, tmp_path):
    assert _run_export(historical_apps, "local", tmp_path) == []


def test_export_covariates_skips_empty_table(db_setup, historical_apps, covariate_model, tmp_path):
    assert _run_export(historical_apps, "prod", tmp_path) == []
