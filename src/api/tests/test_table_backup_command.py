import gzip
import json
import os
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.utils import timezone

from api.models import ArchivedRecord

TABLE = ArchivedRecord._meta.db_table


def _make_archived_record(created_on, model="site"):
    """created_on is auto_now_add, so it has to be backdated with an UPDATE after insert."""
    record = ArchivedRecord.objects.create(app_label="api", model=model, record={"name": "x"})
    ArchivedRecord.objects.filter(pk=record.pk).update(created_on=created_on)
    record.refresh_from_db()
    return record


@pytest.fixture
def aged_records():
    now = timezone.now()
    old = [
        _make_archived_record(now - timedelta(days=1000), model="old_a"),
        _make_archived_record(now - timedelta(days=800), model="old_b"),
    ]
    recent = [_make_archived_record(now - timedelta(days=10), model="recent")]
    return old, recent


@pytest.fixture
def s3_mock():
    """Stand-in for the bucket: uploads add to a set of keys, and existence checks read it, so
    both the pre-upload collision check and the post-upload verification see the same state.
    Yields the upload mock and the key set, which a test can seed with pre-existing objects."""
    keys = set()

    def upload_file(bucket, local_file_path, blob_name, **kwargs):
        keys.add(blob_name)

    with (
        patch(
            "tools.management.commands.table_backup.s3.upload_file", side_effect=upload_file
        ) as upload,
        patch(
            "tools.management.commands.table_backup.s3.file_exists",
            side_effect=lambda bucket, blob_name, **kwargs: blob_name in keys,
        ),
    ):
        yield upload, keys


def _files(tmp_path):
    return sorted(tmp_path.iterdir())


def _read_ndjson(path):
    """Backups are gzipped by default, so the reader picks its opener from the extension."""
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, mode="rt", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def test_backs_up_only_records_older_than_default_cutoff(aged_records, s3_mock, tmp_path):
    old, recent = aged_records
    upload, _ = s3_mock

    call_command("table_backup", TABLE, "--output-dir", str(tmp_path), "--keep-local")

    files = _files(tmp_path)
    assert len(files) == 1
    rows = _read_ndjson(files[0])
    assert {r["model"] for r in rows} == {"old_a", "old_b"}
    assert str(recent[0].pk) not in {r["id"] for r in rows}
    # Nothing is deleted without --delete
    assert ArchivedRecord.objects.filter(pk__in=[r.pk for r in old]).count() == 2
    assert upload.call_count == 1


def test_filename_and_s3_key_pattern(aged_records, s3_mock, tmp_path):
    old, _ = aged_records
    upload, _ = s3_mock

    call_command("table_backup", TABLE, "--output-dir", str(tmp_path), "--keep-local")

    filename = os.path.basename(_files(tmp_path)[0])
    start = min(r.created_on for r in old).strftime("%Y%m%d")
    assert filename.startswith(f"{TABLE}_{start}_")
    assert filename.endswith(".ndjson.gz")

    bucket, local_path, key = upload.call_args.args
    assert key == f"records/{TABLE}/{filename}"
    assert local_path.endswith(filename)
    assert upload.call_args.kwargs["content_type"] == "application/gzip"


def test_existing_s3_key_gets_incremented_suffix(aged_records, s3_mock, tmp_path):
    old, _ = aged_records
    upload, keys = s3_mock
    start = min(r.created_on for r in old).strftime("%Y%m%d")

    call_command("table_backup", TABLE, "--output-dir", str(tmp_path), "--keep-local")
    first_key = upload.call_args.args[2]
    assert keys == {first_key}

    # The suffix goes on the stem, so the .ndjson.gz extensions stay at the end of the name
    call_command("table_backup", TABLE, "--output-dir", str(tmp_path), "--keep-local")
    second_key = upload.call_args.args[2]
    assert second_key == first_key.replace(".ndjson.gz", "_1.ndjson.gz")

    call_command("table_backup", TABLE, "--output-dir", str(tmp_path), "--keep-local")
    assert upload.call_args.args[2] == first_key.replace(".ndjson.gz", "_2.ndjson.gz")

    # Each local file is named to match the key it was uploaded under, so no run overwrites another
    names = {os.path.basename(f) for f in _files(tmp_path)}
    assert len(names) == 3
    assert all(name.startswith(f"{TABLE}_{start}_") for name in names)
    assert {os.path.basename(k) for k in keys} == names


def test_suffix_only_applied_when_key_is_taken(aged_records, s3_mock, tmp_path):
    upload, keys = s3_mock
    keys.add("records/some_other_table/unrelated.ndjson.gz")

    call_command("table_backup", TABLE, "--output-dir", str(tmp_path), "--keep-local")

    assert "_1.ndjson" not in upload.call_args.args[2]


def test_backup_is_gzipped_by_default(aged_records, s3_mock, tmp_path):
    call_command("table_backup", TABLE, "--output-dir", str(tmp_path), "--keep-local")

    path = _files(tmp_path)[0]
    # A real gzip member, not just a .gz name
    with open(path, "rb") as f:
        assert f.read(2) == b"\x1f\x8b"
    assert {r["model"] for r in _read_ndjson(path)} == {"old_a", "old_b"}


def test_no_compress_writes_plain_ndjson(aged_records, s3_mock, tmp_path):
    upload, _ = s3_mock

    call_command(
        "table_backup", TABLE, "--output-dir", str(tmp_path), "--keep-local", "--no-compress"
    )

    path = _files(tmp_path)[0]
    assert os.path.basename(path).endswith(".ndjson")
    with open(path, "rb") as f:
        assert f.read(2) != b"\x1f\x8b"
    assert {r["model"] for r in _read_ndjson(path)} == {"old_a", "old_b"}
    assert upload.call_args.kwargs["content_type"] == "application/x-ndjson"


def test_delete_removes_only_backed_up_records(aged_records, s3_mock, tmp_path):
    old, recent = aged_records

    call_command("table_backup", TABLE, "--output-dir", str(tmp_path), "--delete", "--keep-local")

    assert ArchivedRecord.objects.filter(pk__in=[r.pk for r in old]).count() == 0
    assert ArchivedRecord.objects.filter(pk=recent[0].pk).exists()
    assert len(_read_ndjson(_files(tmp_path)[0])) == 2


def test_local_file_removed_after_upload_by_default(aged_records, s3_mock, tmp_path):
    call_command("table_backup", TABLE, "--output-dir", str(tmp_path))
    assert _files(tmp_path) == []


def test_unverified_upload_aborts_delete(aged_records, tmp_path):
    old, _ = aged_records
    with (
        patch("tools.management.commands.table_backup.s3.upload_file"),
        patch("tools.management.commands.table_backup.s3.file_exists", return_value=False),
        pytest.raises(CommandError, match="could not be verified"),
    ):
        call_command("table_backup", TABLE, "--output-dir", str(tmp_path), "--delete")

    assert ArchivedRecord.objects.filter(pk__in=[r.pk for r in old]).count() == 2


def test_explicit_date_range(aged_records, s3_mock, tmp_path):
    now = timezone.now()
    start = (now - timedelta(days=900)).date().isoformat()
    end = (now - timedelta(days=700)).date().isoformat()

    call_command(
        "table_backup",
        TABLE,
        "--output-dir",
        str(tmp_path),
        "--keep-local",
        f"--start-date={start}",
        f"--end-date={end}",
    )

    path = _files(tmp_path)[0]
    assert {r["model"] for r in _read_ndjson(path)} == {"old_b"}
    expected = f"{TABLE}_{start.replace('-', '')}_{end.replace('-', '')}.ndjson.gz"
    assert os.path.basename(path) == expected


def test_alternate_datetime_field(s3_mock, tmp_path, site1, site2):
    """created_on is the default, but any date/datetime column can drive the filter. Each site is
    aged on one column only, so filtering on updated_on selects a different row than the default."""
    table = site1._meta.db_table
    old = timezone.now() - timedelta(days=1000)
    with connection.cursor() as cursor:
        cursor.execute(f'UPDATE "{table}" SET created_on = %s WHERE id = %s', [old, site1.pk])
        cursor.execute(f'UPDATE "{table}" SET updated_on = %s WHERE id = %s', [old, site2.pk])

    default_dir = tmp_path / "default"
    call_command("table_backup", table, "--output-dir", str(default_dir), "--keep-local")
    assert [r["id"] for r in _read_ndjson(_files(default_dir)[0])] == [str(site1.pk)]

    updated_dir = tmp_path / "updated"
    call_command(
        "table_backup",
        table,
        "--datetime-field=updated_on",
        "--output-dir",
        str(updated_dir),
        "--keep-local",
    )
    assert [r["id"] for r in _read_ndjson(_files(updated_dir)[0])] == [str(site2.pk)]


def test_no_matching_records_writes_nothing(s3_mock, tmp_path):
    upload, _ = s3_mock
    call_command("table_backup", TABLE, "--output-dir", str(tmp_path))
    assert _files(tmp_path) == []
    assert upload.call_count == 0


def test_delete_with_no_upload_is_rejected(tmp_path):
    with pytest.raises(CommandError, match="cannot be used with --no-upload"):
        call_command(
            "table_backup", TABLE, "--output-dir", str(tmp_path), "--delete", "--no-upload"
        )


def test_no_upload_keeps_local_file(aged_records, tmp_path):
    with patch("tools.management.commands.table_backup.s3.upload_file") as upload:
        call_command("table_backup", TABLE, "--output-dir", str(tmp_path), "--no-upload")
    assert len(_files(tmp_path)) == 1
    assert upload.call_count == 0


def test_no_upload_existing_local_file_gets_incremented_suffix(aged_records, tmp_path):
    with patch("tools.management.commands.table_backup.s3.upload_file"):
        call_command("table_backup", TABLE, "--output-dir", str(tmp_path), "--no-upload")
        first = os.path.basename(_files(tmp_path)[0])

        call_command("table_backup", TABLE, "--output-dir", str(tmp_path), "--no-upload")
        call_command("table_backup", TABLE, "--output-dir", str(tmp_path), "--no-upload")

    names = {os.path.basename(f) for f in _files(tmp_path)}
    assert names == {
        first,
        first.replace(".ndjson.gz", "_1.ndjson.gz"),
        first.replace(".ndjson.gz", "_2.ndjson.gz"),
    }


def test_unknown_table_is_rejected(tmp_path):
    with pytest.raises(CommandError, match="does not exist"):
        call_command("table_backup", "no_such_table_here", "--output-dir", str(tmp_path))


def test_unknown_datetime_field_is_rejected(tmp_path):
    with pytest.raises(CommandError, match="has no column"):
        call_command("table_backup", TABLE, "--datetime-field=nope", "--output-dir", str(tmp_path))


def test_non_datetime_field_is_rejected(tmp_path):
    with pytest.raises(CommandError, match="not a date/datetime type"):
        call_command("table_backup", TABLE, "--datetime-field=model", "--output-dir", str(tmp_path))


def test_invalid_identifier_is_rejected(tmp_path):
    with pytest.raises(CommandError, match="not a valid unquoted SQL identifier"):
        call_command("table_backup", 'foo"; DROP TABLE x; --', "--output-dir", str(tmp_path))


def test_start_date_after_end_date_is_rejected(tmp_path):
    with pytest.raises(CommandError, match="must be earlier than"):
        call_command(
            "table_backup",
            TABLE,
            "--output-dir",
            str(tmp_path),
            "--start-date=2025-01-01",
            "--end-date=2024-01-01",
        )


def test_geometry_column_serializes(s3_mock, tmp_path, site1):
    """to_jsonb lets Postgres serialize column types a Python encoder would choke on."""
    table = site1._meta.db_table
    with connection.cursor() as cursor:
        cursor.execute(
            f'UPDATE "{table}" SET created_on = %s WHERE id = %s',
            [timezone.now() - timedelta(days=1000), site1.pk],
        )

    call_command("table_backup", table, "--output-dir", str(tmp_path), "--keep-local")

    rows = _read_ndjson(_files(tmp_path)[0])
    assert len(rows) == 1
    assert rows[0]["id"] == str(site1.pk)
    assert rows[0]["location"] is not None
