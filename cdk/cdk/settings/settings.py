"""
Settings Class
"""
import re
import subprocess
from dataclasses import dataclass

from aws_cdk import Environment


def get_branch_name(strip_punctuation: bool = True) -> str:
    """
    Parse the current branch name.
    """
    # TODO Looks for branch in ENV first, ie - Github actions env var
    git_branch = (
        subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            check=True,
            capture_output=True,
        )
        .stdout.decode("utf-8")
        .strip()
    )

    if strip_punctuation:
        return re.sub("[\W_]+", "", git_branch)

    return git_branch


@dataclass
class VpcSettings:
    """Settings Class for VPCs"""

    az_count: int
    cidr_block: str


@dataclass
class ProjectSettings:
    """Settings Class for Project Envs"""

    # Custom attrs
    cdk_env: Environment
    env_id: str
    # vpc: VpcSettings

    # Common (default) attrs
    branch_name: str = get_branch_name()
