# LetSolo Windows

Windows application installers, release notes, and update files from LetSolo.

## Downloads

Download published installers from this repository's [Releases](https://github.com/letsolo/windows/releases). This repository is not a Homebrew tap. No application binary has been published yet.

## Vapor publisher

The organization-owned `letsolo-vapor` GitHub App is shared with `letsolo/homebrew-macos`. Code authorship, committers, pushes, and release publication must use the actual App bot identity. Administrator accounts may manage repository settings and secrets, but must not submit repository code.

Configure this checkout using the App's private configuration kept outside the repository:

```bash
python3 -I scripts/bot.py --config /absolute/path/to/private/app.json configure
```

The helper detects `letsolo/windows` from its HTTPS origin and requests an installation token scoped to this repository only. It installs repository-local bot identity and hooks, removes inherited GitHub credential helpers, and disables inherited personal commit signing. Authentication failure stops the operation; it never falls back to a personal token.

After configuration, use ordinary `git commit` and `git push`. To publish using `gh` as the bot without switching the global login:

```bash
git bot-gh release list --repo letsolo/windows
```

To verify the latest remote commit:

```bash
python3 -I scripts/bot.py --config /absolute/path/to/private/app.json verify
```

## Actions configuration

Set variable `PUBLISHER_APP_CLIENT_ID` and secret `PUBLISHER_APP_PRIVATE_KEY` before the first push. Install the App only on the two selected release repositories, granting Contents write and Workflows write. The workflow checks the author, committer, and push actor. Local hooks are a checkout safeguard, not a server-enforced access policy.
