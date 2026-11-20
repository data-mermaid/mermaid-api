from datetime import UTC, datetime
from unittest.mock import Mock

import pytest
from record_build_provenance import build_record

SHA = "a" * 40
DIGEST = "sha256:" + "b" * 64


def test_build_record_joins_cdk_artifact_digest_to_full_commit():
    outputs = {
        "api": {
            "BuildGitSha": SHA,
            "ApiImageUri": "123456789012.dkr.ecr.us-east-1.amazonaws.com/assets:asset-hash",
            "ApiTaskDefinitionArn": "arn:task-definition/api:1",
        }
    }
    ecr = Mock()
    ecr.describe_images.return_value = {"imageDetails": [{"imageDigest": DIGEST}]}
    record = build_record(outputs, "api", SHA, "data-mermaid/mermaid-api", ecr, datetime.now(UTC))
    assert record["ImageDigest"] == DIGEST
    assert record["GitSha"] == SHA
    assert record["ImageRepository"].endswith("/assets")
    ecr.describe_images.assert_called_once_with(
        registryId="123456789012", repositoryName="assets", imageIds=[{"imageTag": "asset-hash"}]
    )


@pytest.mark.parametrize("sha", ["unknown", "87845226", "c" * 40])
def test_mismatched_or_short_revisions_never_get_published(sha):
    ecr = Mock()
    with pytest.raises(ValueError):
        build_record({"api": {"BuildGitSha": SHA}}, "api", sha, "org/api", ecr, datetime.now(UTC))
    ecr.describe_images.assert_not_called()
