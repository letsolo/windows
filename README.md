# LetSolo Windows

Windows installers, update files, and release notes for LetSolo products.

## Downloads

Download published installers from [Releases](https://github.com/letsolo/windows/releases). Tags use `<application>-v<version>` so several products can share this repository. No application installers have been released yet.

## Publication flow

A private product repository builds, signs, and tests its Windows app. Its workflow calls `letsolo/github-workflows/.github/workflows/release.yml@v1` with `platform: windows` and the name of an artifact uploaded in the same workflow run. The shared workflow uses Vapor to publish installers and update metadata here, generates `SHA256SUMS`, and creates a draft release by default.

Product-owned build and signing configuration belongs in the source repository. Upload only files intended for public download; credentials and source archives must not be release artifacts.

## Vapor authentication

Author, commit, push, tag, and publish code as `letsolo-vapor[bot]`. Configure a new checkout before its first commit:

```bash
python3 -I scripts/bot.py --config <private-app-config> configure
```

An already configured checkout uses the bot for ordinary `git commit` and `git push`. Use the local alias for bot-authenticated GitHub CLI operations:

```bash
git bot-gh release list
```

```bash
python3 -I scripts/bot.py verify
```

The App is installed across the organization; each local token is restricted to one allowed repository. Keys and private metadata stay outside the checkout. Authentication failure stops the operation, without using a personal login. Local hooks do not create a server-enforced restriction against administrators.

The identity workflow verifies authorship and push identity, then checks tracked files for credentials and personal machine paths. Actions requires variable `PUBLISHER_APP_CLIENT_ID` and encrypted secret `PUBLISHER_APP_PRIVATE_KEY`.
