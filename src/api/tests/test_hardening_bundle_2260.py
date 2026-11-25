"""
Regression tests for Trello card 2260 (low-severity hardening bundle).

Covers the code fixes shipped in this PR:
- L2: clear_collect_records parameterizes its DELETE (latent SQL injection).
- L3: SaveAnnotationSerializer.Meta uses read_only_fields (was the ignored singular
      read_only_field), so is_machine_created is actually read-only.
- L6: get_presigned_url default TTL is 1 day, not 7.

L1 (API-key scoping), L4 (add_profile existence disclosure), L5 (unverified JWT re-parse)
and L7 (image bucket ACL) are feature/behavioral/infra items documented on the card, not
changed here.
"""

import inspect

from api.ingest.utils import clear_collect_records
from api.models import CollectRecord
from api.resources.classification.annotation import SaveAnnotationSerializer
from api.utils.s3 import get_presigned_url


def _cr(project, profile, protocol):
    return CollectRecord.objects.create(
        project=project, profile=profile, data={"protocol": protocol}
    )


def test_clear_collect_records_deletes_only_matching(db_setup, project1, profile1):
    _cr(project1, profile1, "fishbelt")
    _cr(project1, profile1, "fishbelt")
    keep = _cr(project1, profile1, "benthicpit")

    deleted = clear_collect_records(project1.pk, profile1.pk, "fishbelt")
    assert deleted == 2
    assert CollectRecord.objects.filter(pk=keep.pk).exists()


def test_clear_collect_records_handles_quote_safely(db_setup, project1, profile1):
    keep = _cr(project1, profile1, "fishbelt")
    # A protocol value with a quote must not break the query or delete anything.
    deleted = clear_collect_records(project1.pk, profile1.pk, "x' OR '1'='1")
    assert deleted == 0
    assert CollectRecord.objects.filter(pk=keep.pk).exists()


def test_annotation_is_machine_created_is_read_only():
    fields = SaveAnnotationSerializer().get_fields()
    assert fields["is_machine_created"].read_only is True


def test_presigned_url_default_ttl_is_one_day():
    default = inspect.signature(get_presigned_url).parameters["expiration"].default
    assert default == 86_400
