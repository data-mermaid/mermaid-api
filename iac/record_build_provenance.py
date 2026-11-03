"""Append the deployed CDK image digest/full-commit mapping to retained logs."""

import argparse
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path

import boto3


def build_record(outputs, stack, git_sha, repository, ecr, observed_at):
    if not re.fullmatch(r"[0-9a-f]{40}", git_sha):
        raise ValueError("Build provenance requires a full Git SHA")
    output = outputs[stack]
    if output["BuildGitSha"] != git_sha:
        raise ValueError("Deployed CDK build revision differs from the CI revision")
    image = output["ApiImageUri"]
    match = re.fullmatch(
        r"([0-9]{12})\.dkr\.ecr\.([a-z0-9-]+)\.amazonaws\.com/([^:@]+):([^:@]+)", image
    )
    if not match:
        raise ValueError("Expected an ECR image URI with a CDK asset tag")
    account, region, name, tag = match.groups()
    response = ecr.describe_images(
        registryId=account, repositoryName=name, imageIds=[{"imageTag": tag}]
    )
    images = response.get("imageDetails", [])
    if len(images) != 1 or not re.fullmatch(
        r"sha256:[0-9a-f]{64}", images[0].get("imageDigest", "")
    ):
        raise ValueError("ECR did not return a unique image digest")
    return {
        "Type": "BuildProvenance",
        "Repository": repository,
        "GitSha": git_sha,
        "ImageRepository": image.rsplit(":", 1)[0],
        "ImageDigest": images[0]["imageDigest"],
        "ImageTag": tag,
        "AccountId": account,
        "Region": region,
        "TaskDefinitionArn": output["ApiTaskDefinitionArn"],
        "RecordedAt": observed_at.isoformat(),
        "Scope": "CDK build artifact mapping; not proof of incident-time task traffic",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("outputs", type=Path)
    parser.add_argument("stack")
    args = parser.parse_args()
    outputs = json.loads(args.outputs.read_text())
    now = datetime.now(UTC)
    record = build_record(
        outputs,
        args.stack,
        os.environ["GITHUB_SHA"],
        os.environ["GITHUB_REPOSITORY"],
        boto3.client("ecr"),
        now,
    )
    run = os.environ["GITHUB_RUN_ID"]
    attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
    record[
        "RunUrl"
    ] = f"https://github.com/{record['Repository']}/actions/runs/{run}/attempts/{attempt}"
    group = outputs[args.stack]["DeploymentLogGroup"]
    stream = f"build/{record['GitSha']}/{run}-{attempt}"
    logs = boto3.client("logs")
    try:
        logs.create_log_stream(logGroupName=group, logStreamName=stream)
    except logs.exceptions.ResourceAlreadyExistsException:
        pass
    logs.put_log_events(
        logGroupName=group,
        logStreamName=stream,
        logEvents=[{"timestamp": int(now.timestamp() * 1000), "message": json.dumps(record)}],
    )
    print(f"Recorded build provenance in {group} / {stream}")


if __name__ == "__main__":
    main()
