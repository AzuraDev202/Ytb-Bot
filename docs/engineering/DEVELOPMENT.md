# Development and Testing

Run commands from the project root in PowerShell unless otherwise noted.

## Environment

| Component | Requirement |
| --- | --- |
| Operating system | Windows x64 for running and packaging the Windows desktop |
| Python | 3.12, matching the version used in CI |
| Node.js | 22.12+ and npm; CI uses Node.js 22 |
| Web engine | Microsoft Edge WebView2 Runtime |
| Browser testing | Microsoft Edge, as configured in Playwright |
| Build | Git and PyInstaller from the development dependencies |

## Installation

```powershell
git clone https://github.com/AzuraDev202/Ytb-Bot.git
cd Ytb-Bot
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
npm ci --prefix frontend
npm run build --prefix frontend
python gui_app.py
```

Enter your YouTube API key in the application, or create `.env` from the [example](../../.env.example) and set `YOUTUBE_API_KEY`. Keep files containing real keys on the development machine. Gmail has a [separate OAuth guide](../user/CONTACT_COMPOSER.md).

## Run modes

| Command | Purpose |
| --- | --- |
| `python gui_app.py` | Default React desktop |
| `python -m ytb_bot` | The same desktop through the package entry point |
| `npm run dev --prefix frontend` | Preview the frontend in a browser without the Python bridge |
| `python gui_app.py --legacy` | Compatibility CustomTkinter interface |
| `python bot.py` | Compatibility CLI with separate keyword files and Excel exports |

Rebuild the frontend before running the desktop after React changes. `npm run dev` does not provide Python's native file dialogs, SQLite, or Gmail integration.

## Pre-release checks

```powershell
python -m unittest discover -s tests -v
npm run build --prefix frontend
npm test --prefix frontend
python scripts/checks/smoke_react.py
```

After building the EXE, also run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/checks/smoke_desktop.ps1
```

- Python tests cover data, the scanner, bridge, outreach, updater, and legacy interface. Some require working Tk/Tcl, a Windows desktop, or DPAPI.
- Playwright uses a mocked bridge; it does not verify YouTube quota, real OAuth, or actual mail delivery.
- `smoke_react.py` requires a built frontend and an interactive desktop session to check WebView2 and the real bridge.
- `smoke_desktop.ps1` requires `dist/gui_app.exe` and checks the window of the process it launches.
- Report results only after the process exits and returns an exit code. Successful test lines alone are insufficient if the runner remains hung.

Real Google/OAuth checks require an environment and test mailbox controlled by the development team. Do not use channel email addresses as test recipients.

## Language-switch checks

Before release, check English (`en`), Vietnamese (`vi`), and Simplified Chinese (`zh-CN`) in the main React desktop. Switch while keyword edits and a contact draft are unsaved; confirm that neither is discarded and no window reload occurs. Restart and verify preference restoration. Check native prompts and application-authored messages, while ensuring channel data, user keywords, and draft content stay unchanged. Canonical column identifiers and API field keys must remain English. These are verification steps, not a record of completed test results.

## Development tools

```powershell
python scripts/dev/preview_legacy_ui.py --output artifacts/ui/legacy.png
```

This tool captures the legacy interface with sample data and does not scan YouTube. Check screenshots and logs belong in generated directories.

## Troubleshooting

- React does not open: check `frontend/web-dist/index.html` and WebView2 Runtime.
- `init.tcl` errors: check the active Python installation's Tcl/Tk setup; this environment error alone does not establish a logic defect.
- Gmail vault errors: check the Windows account context and DPAPI errors; do not log tokens or fall back to plaintext storage.
- Startup logs: `%LOCALAPPDATA%/Ytb-Bot/logs/desktop.log`.
- Stop Vite or tests holding dependency files before running a release build.

See [architecture](ARCHITECTURE.md), [interface design](UI_DESIGN.md), and [releases](RELEASE.md).
