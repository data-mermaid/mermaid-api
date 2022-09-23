import re
import subprocess


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


def camel_case(string: str) -> str:
    s = re.sub(r"(_|-)+", " ", string).title().replace(" ", "")
    return ''.join([s[0].lower(), s[1:]])