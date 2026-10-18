# Releasing YTB-BOT

## Building on a development machine

Set up the environment using the [development guide](DEVELOPMENT.md), then run from the project root:

```powershell
python scripts/release/build_release.py
```

The script installs frontend dependencies with `npm ci`, builds React, writes commit/build metadata, runs PyInstaller with `packaging/desktop.spec`, and creates a checksum. Build the Windows EXE on Windows x64. Stop Vite and frontend tests before building to avoid locked dependency files.

| Output | Purpose |
| --- | --- |
| `dist/gui_app.exe` | Desktop application with the built frontend |
| `dist/gui_app.exe.sha256` | EXE SHA-256 checksum |
| `dist/build-info.json` | Version, commit, build time, and SHA-256 |

Do not package `.env`, OAuth JSON, or the credential vault. Run the [pre-release checks](DEVELOPMENT.md#pre-release-checks), including the built EXE smoke test. Do not release artifacts from an unverified build.

## Automated releases

The [workflow](../../.github/workflows/release.yml) runs on pushes to `main`, pushes of `v*` tags, or manual dispatch. The repository and Releases must be public so the application can download updates without embedding a GitHub token in the EXE.

- Retain the version for minor changes, fixes, and file reorganization; pushing `main` replaces assets on the release with that version.
- For major changes requiring a new version, update `ytb_bot/version.py` using `X.Y.Z`. If using a tag, it must match `vX.Y.Z`.
- Lower versions cannot be released; pushing a tag matching the current version again does not overwrite a build from `main`.
- The workflow tests Python, builds React/the EXE, and tests the UI, bridge, and EXE window before publishing.
- Assets include `gui_app.exe`, `gui_app.exe.sha256`, and `build-info.json`.

Do not commit build files or real keys. For manual releases, keep the EXE, checksum, and metadata from the same build. Before wider distribution, test updating between two EXEs on Windows and confirm that local data remains intact.
