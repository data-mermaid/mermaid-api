import gzip
import json
import os
from contextlib import contextmanager
from datetime import timedelta
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from django.conf import settings
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


@contextmanager
def _s3_patches(on_upload=None):
    """Stand-in for the bucket: uploads record the key and the size of the file that was sent, and
    both the pre-upload collision check and the post-upload verification read that state back, so
    a run sees the bucket as it left it. on_upload runs after the object is recorded, for tests
    that need something to happen while the upload is in flight.

    Yields the upload mock and the {key: size} dict, which a test can seed with pre-existing
    objects or edit to stand in for an object that is not the one that was uploaded."""
    objects = {}

    def upload_file(bucket, local_file_path, blob_name, **kwargs):
        objects[blob_name] = os.path.getsize(local_file_path)
        if on_upload is not None:
            on_upload(bucket, local_file_path, blob_name, **kwargs)

    def head_object(bucket, blob_name, **kwargs):
        if blob_name not in objects:
            return None
        return {"ContentLength": objects[blob_name]}

    with (
        patch(
            "tools.management.commands.table_backup.s3.upload_file", side_effect=upload_file
        ) as upload,
        patch(
            "tools.management.commands.table_backup.s3.file_exists",
            side_effect=lambda bucket, blob_name, **kwargs: blob_name in objects,
        ),
        patch("tools.management.commands.table_backup.s3.head_object", side_effect=head_object),
    ):
        yield upload, objects


@pytest.fixture
def s3_mock():
    with _s3_patches() as patches:
        yield patches


@contextmanager
def _terminal(answer):
    """Stand in for a user at a terminal answering the --delete confirmation prompt."""
    stdin = MagicMock()
    stdin.isatty.return_value = True
    with (
        patch("tools.management.commands.table_backup.sys.stdin", stdin),
        patch("builtins.input", return_value=answer) as prompt,
    ):
        yield prompt


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
    assert set(keys) == {first_key}

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
    keys["records/some_other_table/unrelated.ndjson.gz"] = 0

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

    call_command(
        "table_backup",
        TABLE,
        "--output-dir",
        str(tmp_path),
        "--delete",
        "--noinput",
        "--keep-local",
    )

    assert ArchivedRecord.objects.filter(pk__in=[r.pk for r in old]).count() == 0
    assert ArchivedRecord.objects.filter(pk=recent[0].pk).exists()
    assert len(_read_ndjson(_files(tmp_path)[0])) == 2


def test_delete_skips_records_updated_out_of_range_during_backup(aged_records, tmp_path):
    """A record whose datetime field moves out of the backed up range between the read and the
    delete no longer matches the filter, so it is left in place."""
    old, _ = aged_records
    bumped, still_old = old

    def upload_file(bucket, local_file_path, blob_name, **kwargs):
        # Stands in for a concurrent update landing while the backup is being uploaded.
        ArchivedRecord.objects.filter(pk=bumped.pk).update(created_on=timezone.now())

    out = StringIO()
    with _s3_patches(on_upload=upload_file):
        call_command(
            "table_backup",
            TABLE,
            "--output-dir",
            str(tmp_path),
            "--delete",
            "--noinput",
            "--keep-local",
            stdout=out,
        )

    assert ArchivedRecord.objects.filter(pk=bumped.pk).exists()
    assert not ArchivedRecord.objects.filter(pk=still_old.pk).exists()
    assert "1 backed up record(s) no longer match the filter" in out.getvalue()
    # The record that was left behind is still in the backup file.
    assert len(_read_ndjson(_files(tmp_path)[0])) == 2


def test_delete_batches_are_committed_independently(aged_records, s3_mock, tmp_path):
    """Each batch commits on its own, so a failure part way through keeps the batches that
    already succeeded instead of rolling the whole delete back."""
    old, _ = aged_records
    first, second = old  # backed up oldest first, so each is its own batch

    real_cursor = connection.cursor
    deletes = []

    class FailingCursor:
        """Delegates to a real cursor but blows up on the second DELETE."""

        def __init__(self, inner):
            self._inner = inner

        def __getattr__(self, name):
            return getattr(self._inner, name)

        def execute(self, sql, params=None):
            if sql.lstrip().startswith("DELETE"):
                deletes.append(sql)
                if len(deletes) == 2:
                    raise RuntimeError("connection lost")
            return self._inner.execute(sql, params)

    @contextmanager
    def failing_cursor():
        with real_cursor() as cursor:
            yield FailingCursor(cursor)

    out = StringIO()
    with (
        patch("tools.management.commands.table_backup.DELETE_BATCH_SIZE", 1),
        patch.object(connection, "cursor", failing_cursor),
        pytest.raises(RuntimeError, match="connection lost"),
    ):
        call_command(
            "table_backup",
            TABLE,
            "--output-dir",
            str(tmp_path),
            "--delete",
            "--noinput",
            stdout=out,
        )

    assert not ArchivedRecord.objects.filter(pk=first.pk).exists()
    assert ArchivedRecord.objects.filter(pk=second.pk).exists()
    assert "Delete failed after 1 of 2 record(s)" in out.getvalue()


def test_delete_spans_multiple_batches(aged_records, s3_mock, tmp_path):
    """With more eligible records than fit in a batch, every batch is deleted -- including a
    final partial one -- and the reported count is the sum across them."""
    old, recent = aged_records
    now = timezone.now()
    # 5 old records against a batch size of 2 gives batches of 2, 2 and 1, so a dropped tail or
    # an off-by-one in the slicing leaves records behind.
    old = old + [
        _make_archived_record(now - timedelta(days=900 - i), model=f"old_extra_{i}")
        for i in range(3)
    ]

    out = StringIO()
    with patch("tools.management.commands.table_backup.DELETE_BATCH_SIZE", 2):
        call_command(
            "table_backup",
            TABLE,
            "--output-dir",
            str(tmp_path),
            "--delete",
            "--noinput",
            "--keep-local",
            stdout=out,
        )

    assert ArchivedRecord.objects.filter(pk__in=[r.pk for r in old]).count() == 0
    assert ArchivedRecord.objects.filter(pk=recent[0].pk).exists()
    assert f"Deleted {len(old)} record(s)" in out.getvalue()
    assert "no longer match the filter" not in out.getvalue()
    assert len(_read_ndjson(_files(tmp_path)[0])) == len(old)


def test_local_file_removed_after_upload_by_default(aged_records, s3_mock, tmp_path):
    call_command("table_backup", TABLE, "--output-dir", str(tmp_path))
    assert _files(tmp_path) == []


def test_unverified_upload_aborts_delete(aged_records, tmp_path):
    """No object at the key it was just uploaded to: the records stay put."""
    old, _ = aged_records
    with (
        patch("tools.management.commands.table_backup.s3.upload_file"),
        patch("tools.management.commands.table_backup.s3.file_exists", return_value=False),
        patch("tools.management.commands.table_backup.s3.head_object", return_value=None),
        pytest.raises(CommandError, match="could not be verified"),
    ):
        call_command("table_backup", TABLE, "--output-dir", str(tmp_path), "--delete", "--noinput")

    assert ArchivedRecord.objects.filter(pk__in=[r.pk for r in old]).count() == 2


def test_upload_of_a_different_size_aborts_delete(aged_records, tmp_path):
    """An object at the key is not enough -- a concurrent run can put a different object there,
    and a transfer can produce a short one. A size that does not match the local backup file
    means the object is not the backup that was just written, so nothing is deleted."""
    old, _ = aged_records

    def truncate_uploaded_object(bucket, local_file_path, blob_name, **kwargs):
        objects[blob_name] = objects[blob_name] - 1

    with _s3_patches(on_upload=truncate_uploaded_object) as (_, objects):
        with pytest.raises(CommandError, match="is not the file that was just uploaded"):
            call_command(
                "table_backup", TABLE, "--output-dir", str(tmp_path), "--delete", "--noinput"
            )

    assert ArchivedRecord.objects.filter(pk__in=[r.pk for r in old]).count() == 2


def test_dry_run_reports_without_backing_up_or_deleting(aged_records, s3_mock, tmp_path):
    old, _ = aged_records
    upload, keys = s3_mock

    out = StringIO()
    call_command(
        "table_backup", TABLE, "--output-dir", str(tmp_path), "--delete", "--dry-run", stdout=out
    )

    output = out.getvalue()
    assert "would back up 2 record(s)" in output
    assert f"would then delete those 2 record(s) from {TABLE}" in output
    assert f"s3://{settings.AWS_BACKUP_BUCKET}/records/{TABLE}/{TABLE}_" in output
    assert not tmp_path.exists() or _files(tmp_path) == []
    assert upload.call_count == 0
    assert keys == {}
    assert ArchivedRecord.objects.filter(pk__in=[r.pk for r in old]).count() == 2


def test_dry_run_reports_the_local_path_with_no_upload(aged_records, s3_mock, tmp_path):
    out = StringIO()
    call_command(
        "table_backup", TABLE, "--output-dir", str(tmp_path), "--no-upload", "--dry-run", stdout=out
    )

    assert f"would back up 2 record(s) to {tmp_path}{os.path.sep}{TABLE}_" in out.getvalue()
    assert not tmp_path.exists() or _files(tmp_path) == []


def test_delete_asks_for_confirmation(aged_records, s3_mock, tmp_path):
    old, _ = aged_records

    out = StringIO()
    with _terminal("yes") as prompt:
        call_command("table_backup", TABLE, "--output-dir", str(tmp_path), "--delete", stdout=out)

    assert prompt.call_count == 1
    assert f"permanently remove 2 record(s) from {TABLE}" in out.getvalue()
    assert ArchivedRecord.objects.filter(pk__in=[r.pk for r in old]).count() == 0


def test_declining_the_confirmation_backs_up_nothing(aged_records, s3_mock, tmp_path):
    """The prompt comes before the backup is written, so a cancelled run leaves no partial work."""
    old, _ = aged_records
    upload, _ = s3_mock

    with _terminal("no"), pytest.raises(CommandError, match="Cancelled"):
        call_command("table_backup", TABLE, "--output-dir", str(tmp_path), "--delete")

    assert ArchivedRecord.objects.filter(pk__in=[r.pk for r in old]).count() == 2
    assert upload.call_count == 0
    assert not tmp_path.exists() or _files(tmp_path) == []


def test_delete_without_a_terminal_requires_noinput(aged_records, s3_mock, tmp_path):
    """A scheduled run has no one to answer the prompt, so it has to confirm up front rather than
    have the answer assumed for it."""
    old, _ = aged_records
    upload, _ = s3_mock
    stdin = MagicMock()
    stdin.isatty.return_value = False

    with (
        patch("tools.management.commands.table_backup.sys.stdin", stdin),
        pytest.raises(CommandError, match="no terminal to prompt on"),
    ):
        call_command("table_backup", TABLE, "--output-dir", str(tmp_path), "--delete")

    assert ArchivedRecord.objects.filter(pk__in=[r.pk for r in old]).count() == 2
    assert upload.call_count == 0


def test_noinput_does_not_prompt(aged_records, s3_mock, tmp_path):
    old, _ = aged_records

    with _terminal("no") as prompt:
        call_command("table_backup", TABLE, "--output-dir", str(tmp_path), "--delete", "--noinput")

    assert prompt.call_count == 0
    assert ArchivedRecord.objects.filter(pk__in=[r.pk for r in old]).count() == 0


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


@pytest.fixture
def pkless_table():
    """A table with rows but no primary key. Rolled back with the test transaction."""
    name = "table_backup_pkless"
    with connection.cursor() as cursor:
        cursor.execute(f"CREATE TABLE {name} (model text, created_on timestamptz)")
        cursor.execute(
            f"INSERT INTO {name} (model, created_on) VALUES ('a', now() - interval '1000 days')"
        )
    yield name
    with connection.cursor() as cursor:
        cursor.execute(f"DROP TABLE {name}")


def test_delete_on_table_without_primary_key_fails_before_any_work(pkless_table, tmp_path):
    """The primary key is checked up front, so no table scan, output directory or S3 lookup
    happens on a table --delete can never work on."""
    with (
        patch("tools.management.commands.table_backup.s3.file_exists") as file_exists,
        pytest.raises(CommandError, match="has no primary key"),
    ):
        call_command(
            "table_backup",
            pkless_table,
            "--output-dir",
            str(tmp_path / "unmade"),
            "--delete",
        )

    assert file_exists.call_count == 0
    assert not (tmp_path / "unmade").exists()


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


def test_partial_write_is_cleaned_up_and_leaves_the_name_free(aged_records, tmp_path):
    """A failed run must not leave a truncated file behind: it would read as a valid backup, and
    the retry would be pushed onto a suffixed name instead of the one it asked for."""

    def fail_after_partial_write(file_path, compress):
        with open(file_path, "w", encoding="utf-8") as f:
            f.write('{"partial": true}\n')
        raise OSError("No space left on device")

    with patch("tools.management.commands.table_backup.s3.upload_file"):
        with patch(
            "tools.management.commands.table_backup.Command._open_backup_file",
            side_effect=fail_after_partial_write,
        ):
            with pytest.raises(OSError, match="No space left on device"):
                call_command("table_backup", TABLE, "--output-dir", str(tmp_path), "--no-upload")

        assert _files(tmp_path) == []

        call_command("table_backup", TABLE, "--output-dir", str(tmp_path), "--no-upload")

    files = _files(tmp_path)
    assert len(files) == 1
    assert "_1." not in os.path.basename(files[0])
    assert len(_read_ndjson(files[0])) == 2


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
