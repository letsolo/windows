#!/usr/bin/env python3
"""Repository-local commit and push guard for the configured App bot."""
import subprocess
import sys

REPOSITORIES = ("homebrew-macos", "windows", "android", "github-workflows")


def git(*args):
    return subprocess.check_output(["git", *args], text=True).strip()


def guard():
    repository = git("config", "--local", "--get", "letsolo.repository")
    if repository not in REPOSITORIES:
        raise ValueError("Unexpected release repository")
    remote = f"https://github.com/letsolo/{repository}.git"
    name = git("config", "--local", "--get", "letsolo.botName")
    email = git("config", "--local", "--get", "letsolo.botEmail")
    if not name.endswith("[bot]") or not email.endswith("@users.noreply.github.com"):
        raise ValueError("Missing bot identity")
    expected = f"{name} <{email}>"
    for variable in ("GIT_AUTHOR_IDENT", "GIT_COMMITTER_IDENT"):
        if not git("var", variable).startswith(expected + " "):
            raise ValueError("Author or committer does not match the configured bot")
    if len(sys.argv) > 1:
        if len(sys.argv) != 3 or sys.argv[1] != "origin" or sys.argv[2] != remote:
            raise ValueError("Unexpected push destination")
        for line in sys.stdin:
            _local_ref, local_sha, _remote_ref, remote_sha = line.split()
            if not local_sha.strip("0"):
                continue
            if remote_sha.strip("0"):
                revisions = [f"{remote_sha}..{local_sha}"]
            else:
                revisions = [local_sha, "--not", "--remotes=origin"]
            for sha in git("rev-list", *revisions).splitlines():
                actual = git("show", "-s", "--format=%an <%ae>%n%cn <%ce>", sha)
                if actual.splitlines() != [expected, expected]:
                    raise ValueError("Push contains a commit by another identity")


if __name__ == "__main__":
    try:
        guard()
    except (ValueError, OSError, subprocess.SubprocessError):
        print("Blocked: author, committer, destination, and pushed commits must match the configured App bot.", file=sys.stderr)
        raise SystemExit(1)
