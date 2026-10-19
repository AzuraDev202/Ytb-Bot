# YTB-BOT Creator Studio

A Windows desktop application for keyword-based YouTube channel discovery, local data exploration, and reviewed Gmail messaging.

This public repository provides a practical reference for integrating a React interface with a Python backend through pywebview. It demonstrates background API requests, SQLite persistence, OAuth authorization, Windows credential protection, and desktop packaging. You can run the application or study its components independently.

[Download for Windows](https://github.com/AzuraDev202/Ytb-Bot/releases/latest/download/gui_app.exe) | [User guide](docs/user/DESKTOP_GUIDE.md) | [Documentation](docs/README.md) | [Report an issue](https://github.com/AzuraDev202/Ytb-Bot/issues)

## What the application does

1. **Prepare keywords.** Enter topics, edit the keyword table, or import a column from an Excel workbook.
2. **Discover channels.** Search recent videos through YouTube Data API v3, retrieve channel metadata, and apply channel-age, total-view, and public-contact filters.
3. **Explore saved data.** Search, sort, paginate, and inspect results stored in a local SQLite database. Channel IDs prevent duplicate entries across scans.
4. **Review contact groups.** Group channels that share an email address or supported social link. A shared email becomes one selectable recipient.
5. **Compose and review messages.** Connect a Gmail account through OAuth, save drafts, review recipients and content, and explicitly start an individual or bulk send.

The main desktop supports English, Vietnamese, and Simplified Chinese, light and dark themes, responsive layouts, and optional motion effects. The command-line interface (CLI) and legacy CustomTkinter interface remain available for compatibility with earlier Excel workflows.

## Quick start

### Run the Windows application

You need Windows 10/11 x64, Microsoft Edge WebView2 Runtime, an internet connection, and a YouTube Data API v3 key. An API key identifies your Google Cloud project when the application requests public YouTube data.

1. Download `gui_app.exe` from the [latest release](https://github.com/AzuraDev202/Ytb-Bot/releases/latest).
2. Place it in a writable folder and open it.
3. Enter your API key, add keywords, and select **Start discovery**.
4. Open **Results** to explore saved scans or **Grouped contacts** to inspect contact associations.

The packaged application includes the frontend and Python runtime; Python, Node.js, and Microsoft Excel are not required to run it. Release assets include a [SHA-256 checksum](https://github.com/AzuraDev202/Ytb-Bot/releases/latest/download/gui_app.exe.sha256) for checking the downloaded file's integrity.

Gmail is optional and uses [separate OAuth configuration](docs/user/CONTACT_COMPOSER.md). A YouTube API key does not authorize email sending. OAuth lets you grant account permissions through Google's browser sign-in flow.

Hướng dẫn tiếng Việt: [Thiết lập Google OAuth, kết nối Gmail và tự làm mới token](docs/user/GOOGLE_OAUTH_VI.md).

### Run from source

Use Python 3.12 and Node.js 22.12+ with npm on Windows. From PowerShell:

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

Enter the YouTube API key in the interface, or configure `YOUTUBE_API_KEY` using [`.env.example`](.env.example). Rebuild the frontend after changing React code before launching the desktop. The [development guide](docs/engineering/DEVELOPMENT.md) covers browser previews, CLI mode, and troubleshooting.

## Technical overview

| Component | Role |
| --- | --- |
| React and TypeScript | Interface components, editor state, and typed desktop-bridge calls |
| Vite | Frontend development server and production bundle |
| Python and pywebview | Native window, JavaScript-to-Python bridge, and application services |
| Edge WebView2 | Embedded browser engine used by the Windows desktop |
| YouTube Data API v3 | Video search and public channel metadata |
| SQLite | Local keywords, scan results, drafts, and send-attempt history |
| Gmail API and OAuth | Account authorization and explicitly reviewed email sends |
| Windows DPAPI | Data Protection API used to encrypt saved Gmail credentials for the current Windows account |
| PyInstaller and GitHub Actions | Windows executable packaging and automated verification/release workflows |

The frontend requests operations through the desktop bridge. Python performs network and storage operations; the scanner runs in a background thread so the interface can remain responsive. See [Architecture](docs/engineering/ARCHITECTURE.md) for the directory map and processing flow.

## Behavior and limitations

- **Keyword-based discovery:** results depend on search terms, API ranking, page depth, and available request quota. A request quota limits API usage; it does not describe the number of channels available. Searches do not enumerate every YouTube channel or automatically translate keywords.
- **Channel eligibility:** the scanner accepts channels within the selected age/view thresholds that expose a supported contact in their public description. It skips Channel IDs already saved locally. Keywords in multiple languages can broaden discovery; changing the interface language does not change search terms.
- **Saved snapshots:** channel metrics reflect the time of scanning and do not refresh automatically. Collected batches remain available when a scan is stopped or encounters an API error; an in-flight request may not yet be persisted.
- **Reviewed messaging:** bulk mail sends a separate message to each unique selected email address, with an application cap of 100 email groups and a two-second pause between sends. These safeguards are separate from Google's account and API limits.
- **Send outcomes:** Gmail accepting a request does not confirm delivery. The application records individual outcomes, skips previously attempted recipients for the same sender when preparing bulk mail, and does not automatically retry uncertain requests. Check Gmail Sent before further contact with an uncertain recipient.
- **Social contacts:** the application supports copying a message and opening a saved profile; sending on that platform remains a manual action.

## Local data and account access

| Data | Storage |
| --- | --- |
| Keywords, scans, drafts, and send history | `%LOCALAPPDATA%/Ytb-Bot/data/workspace.sqlite3` |
| YouTube API key | `.env` beside the EXE, or in the repository root when running from source |
| Gmail configuration and tokens | `%LOCALAPPDATA%/Ytb-Bot/data/mail/credentials.bin`, encrypted with Windows DPAPI |
| Desktop preferences | `studio-settings.json` beside the EXE or at the repository root, plus browser-local preferences |

Gmail permissions cover sending and identifying the connected email account; the application does not request inbox read access. Imported workbooks are read without modifying the source file. The application connects to Google for API operations and sign-in, and to GitHub for update checks and downloads.

Keep API keys, OAuth files, credentials, and personal data out of commits and issue reports. See the [backup and troubleshooting guide](docs/user/DESKTOP_GUIDE.md#data-and-troubleshooting).

## Verification

```powershell
python -m unittest discover -s tests -v
npm run build --prefix frontend
npm test --prefix frontend
python scripts/checks/smoke_react.py
```

Python tests cover application services and persistence. Browser tests use a mocked desktop bridge; the native smoke check exercises the real WebView2 window. Some checks require an interactive Windows session, Tk/Tcl, Microsoft Edge, or DPAPI. Mock-based tests do not establish real YouTube API access, Gmail sign-in, or email delivery. See [Development and testing](docs/engineering/DEVELOPMENT.md) for prerequisites and verification scope.

## Documentation and contributions

| Guide | Start here when you want to... |
| --- | --- |
| [Documentation index](docs/README.md) | Find a guide by task |
| [Desktop guide](docs/user/DESKTOP_GUIDE.md) | Configure keywords, inspect results, and back up local data |
| [Contact composer](docs/user/CONTACT_COMPOSER.md) | Set up Gmail OAuth and understand draft/send states |
| [Architecture](docs/engineering/ARCHITECTURE.md) | Understand module boundaries and data flow |
| [Development and testing](docs/engineering/DEVELOPMENT.md) | Set up the environment and run checks |
| [Interface design](docs/engineering/UI_DESIGN.md) | Understand layout, localization, and interaction conventions |
| [Build and release](docs/engineering/RELEASE.md) | Package the Windows executable and understand CI |

For bug reports, include reproduction steps, the application version, and relevant diagnostics with credentials removed. For proposed changes, describe the expected behavior and checks performed in the issue or pull request.

## License

The source code is distributed under the [Apache License 2.0](LICENSE).
