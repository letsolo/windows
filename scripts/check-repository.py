#!/usr/bin/env python3
"""Check tracked repository files for credentials and machine-specific paths."""
import re
import subprocess
import sys
from pathlib import Path

RULES = {
    "private key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "GitHub token": re.compile(rb"(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,})"),
    "personal home path": re.compile(rb"(?:/" rb"Users/[^/\s]+/|/" rb"home/[^/\s]+/|[A-Z]:\\Users\\[^\\\s]+\\)"),
    "credential URL": re.compile(rb"https://[^\s/@:]+:[^\s/@]+@github\.com"),
}


def main():
    names = subprocess.check_output(["git", "ls-files", "-z"]).split(b"\0")
    failures = []
    for raw_name in filter(None, names):
        path = Path(raw_name.decode())
        if not path.is_file() or path.is_symlink():
            continue
        data = path.read_bytes()
        for label, pattern in RULES.items():
            if pattern.search(data):
                failures.append(f"{path}: {label}")
        if path.name.endswith((".pem", ".key", ".p12", ".p8", ".jks", ".keystore")):
            failures.append(f"{path}: credential file")
    if failures:
        print("Repository privacy check failed:", file=sys.stderr)
        print("\n".join(failures), file=sys.stderr)
        return 1
    print("Tracked files contain no detected credentials or personal machine paths.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
