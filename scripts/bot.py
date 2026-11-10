#!/usr/bin/env python3
"""Authenticate only as a scoped LetSolo Vapor App installation."""
import argparse
import base64
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

OWNER = "letsolo"
REPOSITORIES = ("homebrew-macos", "windows", "android", "github-workflows")


def api(path, token, data=None):
    body = None if data is None else json.dumps(data).encode()
    request = Request(
        "https://api.github.com" + path,
        data=body,
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "letsolo-vapor",
            "Content-Type": "application/json",
        },
    )
    with urlopen(request, timeout=25) as response:
        return json.load(response)


def b64(value):
    return base64.urlsafe_b64encode(value).rstrip(b"=")


def app_jwt(config):
    now = int(time.time())
    claims = {"iat": now - 60, "exp": now + 540, "iss": str(config["app_id"])}
    signing_input = b64(b'{"alg":"RS256","typ":"JWT"}') + b"." + b64(json.dumps(claims).encode())
    signed = subprocess.run(
        ["openssl", "dgst", "-sha256", "-sign", str(config["private_key"])],
        input=signing_input, capture_output=True, check=True,
    )
    return (signing_input + b"." + b64(signed.stdout)).decode()


def repository_name(config):
    repository = config["repository"]
    allowed = config.get("repositories", [repository])
    if config["owner"] != OWNER or repository not in REPOSITORIES or repository not in allowed:
        raise ValueError("Unexpected repository in App configuration")
    return repository


def remote_url(repository):
    return f"https://github.com/{OWNER}/{repository}.git"


def origin_repository():
    origin = git("remote", "get-url", "origin")
    for repository in REPOSITORIES:
        if origin == remote_url(repository):
            return repository
    raise ValueError("Expected a LetSolo release repository origin")


def installation_token(config):
    repository = repository_name(config)
    jwt = app_jwt(config)
    installation = api(f"/repos/{OWNER}/{repository}/installation", jwt)
    if installation["account"]["login"].lower() != OWNER:
        raise ValueError("Unexpected installation owner")
    if installation["app_id"] != int(config["app_id"]):
        raise ValueError("Unexpected installed App")
    result = api(
        f'/app/installations/{installation["id"]}/access_tokens', jwt,
        {"repositories": [repository], "permissions": {"contents": "write", "workflows": "write"}},
    )
    return result["token"]


def identity(config, token):
    name = config["slug"] + "[bot]"
    user = api("/users/" + name.replace("[", "%5B").replace("]", "%5D"), token)
    if user["type"] != "Bot" or user["login"] != name:
        raise ValueError("Expected the GitHub App bot identity")
    return name, f'{user["id"]}+{name}@users.noreply.github.com'


def git(*args):
    return subprocess.check_output(["git", *args], text=True).strip()


def configure(config, config_path):
    repository = repository_name(config)
    expected_remote = remote_url(repository)
    if git("remote", "get-url", "origin") != expected_remote:
        raise ValueError("Unexpected LetSolo HTTPS origin")
    if git("remote", "get-url", "--push", "origin") != expected_remote:
        raise ValueError("Unexpected push destination")
    token = installation_token(config)
    name, email = identity(config, token)
    hook_source = Path(__file__).with_name("check-bot-identity.py")
    hooks = Path(git("rev-parse", "--absolute-git-dir")) / "letsolo-hooks"
    hooks.mkdir(mode=0o700, exist_ok=True)
    for hook in ("pre-commit", "pre-push"):
        target = hooks / hook
        target.write_bytes(hook_source.read_bytes())
        target.chmod(0o700)
    values = {
        "user.name": name, "user.email": email, "user.useConfigOnly": "true",
        "commit.gpgSign": "false", "tag.gpgSign": "false",
        "letsolo.botName": name, "letsolo.botEmail": email, "letsolo.repository": repository,
        "letsolo.appConfig": str(config_path),
        "core.hooksPath": str(hooks), "credential.useHttpPath": "true",
        "http.extraHeader": "", "http.https://github.com/.extraHeader": "",
    }
    for key, value in values.items():
        git("config", "--local", key, value)
    helper = [
        sys.executable, "-I", str(Path(__file__).resolve()),
        "--config", str(config_path), "--repository", repository,
    ]
    command = "!" + shlex.join([*helper, "credential"])
    git("config", "--local", "alias.bot-gh", "!" + shlex.join([*helper, "gh"]))
    for key in ("credential.helper", "credential.https://github.com.helper"):
        git("config", "--local", "--replace-all", key, "")
        git("config", "--local", "--add", key, command)
    print(json.dumps({"repository": f"{OWNER}/{repository}", "bot": name, "email": email}))


def credential(config, operation):
    if operation != "get":
        return
    fields = {}
    for line in sys.stdin:
        line = line.rstrip("\n")
        if not line:
            break
        key, _, value = line.partition("=")
        fields[key] = value
    if fields.get("protocol") != "https" or fields.get("host") != "github.com":
        raise ValueError("Unexpected credential destination")
    repository = repository_name(config)
    if fields.get("path", "").removesuffix(".git") != f"{OWNER}/{repository}":
        raise ValueError("Unexpected credential repository")
    token = installation_token(config)
    # Git credential-helper protocol output; never invoke manually to inspect a token.
    sys.stdout.write(f"username=x-access-token\npassword={token}\n\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=os.environ.get("LETSOLO_APP_CREDENTIALS"))
    parser.add_argument("--repository", choices=REPOSITORIES)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("configure")
    sub.add_parser("verify")
    creds = sub.add_parser("credential")
    creds.add_argument("operation", choices=("get", "store", "erase"))
    cli = sub.add_parser("gh")
    cli.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    try:
        if not args.config:
            args.config = git("config", "--local", "--get", "letsolo.appConfig")
        if not args.config:
            raise ValueError("An external private App configuration is required")
        config_path = Path(args.config).resolve()
        config = json.loads(config_path.read_text())
        config["repository"] = args.repository or config.get("repository") or origin_repository()
        repository = repository_name(config)
        if args.command == "credential":
            credential(config, args.operation)
        elif args.command == "configure":
            configure(config, config_path)
        else:
            token = installation_token(config)
            name, _email = identity(config, token)
            if args.command == "gh":
                env = os.environ.copy()
                env["GH_TOKEN"] = token
                env.pop("GITHUB_TOKEN", None)
                return subprocess.call(["gh", *args.arguments], env=env)
            commit = api(f"/repos/{OWNER}/{repository}/commits/HEAD", token)
            for field in ("author", "committer"):
                if (commit.get(field) or {}).get("login") != name:
                    raise ValueError("Remote commit does not belong to the App bot")
            print(json.dumps({"sha": commit["sha"], "author": name, "committer": name}))
    except (OSError, ValueError, KeyError, HTTPError, URLError, subprocess.SubprocessError):
        if args.command == "credential":
            sys.stdout.write("quit=true\n\n")
        print("Bot authentication or identity check failed; personal-account fallback is disabled.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
