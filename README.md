# YTB-BOT Creator Studio

**Discover new YouTube channels. Screen opportunities. Manage your research in one application.**

YTB-BOT is a Windows application for YouTube market researchers and people seeking creators to collaborate with. Starting from a list of topics, it finds channels by channel age and total views, then saves results with public contact details for review and follow-up.

[Download for Windows](https://github.com/AzuraDev202/Ytb-Bot/releases/latest/download/gui_app.exe) Â· [User guide](docs/user/DESKTOP_GUIDE.md) Â· [Documentation](docs/README.md) Â· [Report an issue](https://github.com/AzuraDev202/Ytb-Bot/issues)

## From topics to a channel shortlist

1. **Prepare keywords:** enter topics, paste a list, or import an Excel column.
2. **Choose filters:** set the maximum channel age, minimum views, and search depth.
3. **Review results:** compare metrics, search, sort, and inspect contact details.
4. **Continue your work:** revisit history, copy data, or compose an email for a selected channel.

## Features

| Task | Capabilities |
| --- | --- |
| Discovery | Search videos by keyword and inspect channels through YouTube Data API v3 |
| Screening | Filter by channel age, total views, and public contacts; exclude Channel IDs already saved in history |
| Keyword management | Edit a table, add/delete rows, paste multiple lines, and import `.xlsx`/`.xls` |
| Result storage | Keep scan history, including partial results when stopped or interrupted by API errors |
| Data review | Search, sort, paginate, view details, and copy |
| Outreach | Connect multiple Gmail accounts through OAuth, save drafts, review before sending, and view send history |
| Desktop | English, Vietnamese, and Simplified Chinese interfaces; light/dark themes, responsive layouts, and updates from GitHub Releases |

These features belong to the default React desktop. The CLI and `--legacy` interface retain separate Excel export workflows for compatibility.

## Getting started

**Requirements:** Windows 10/11 x64, Microsoft Edge WebView2 Runtime, an Internet connection, and a YouTube Data API v3 key with available quota.

1. Download `gui_app.exe` from the [latest release](https://github.com/AzuraDev202/Ytb-Bot/releases/latest).
2. Place the file in a writable folder and open the application.
3. Enter your API key, add keywords, and select **Start discovery**.
4. Open **Results** to review and manage saved channels.

The standalone EXE requires no Python, Node.js, or Microsoft Excel installation. A [SHA-256 checksum](https://github.com/AzuraDev202/Ytb-Bot/releases/latest/download/gui_app.exe.sha256) accompanies each release.

Use the desktop language selector to switch between English (`en`), Vietnamese (`vi`), and Simplified Chinese (`zh-CN`). The choice is saved locally and in desktop preferences; switching applies immediately without reloading or discarding drafts. See [language settings](docs/user/DESKTOP_GUIDE.md#interface-language) for scope.

Sending email requires separate [Gmail OAuth setup](docs/user/CONTACT_COMPOSER.md). For social networks, the application lets you copy your message and open a profile to send it manually.

## Data and permissions

- **Keywords, results, drafts, and send history** are stored in `%LOCALAPPDATA%/Ytb-Bot/data/workspace.sqlite3`.
- **The API key** is stored in `.env` beside the EXE, or in the project root when running from source.
- **Gmail credentials** are encrypted with Windows DPAPI for the Windows account. The application requests permission to send mail and identify the email address; it does not read the inbox.
- **Imported Excel files** are read only. The default desktop stores results in SQLite.
- **Connected services:** Google for search, sign-in, and sending mail; GitHub for application updates.

See the [backup and troubleshooting guide](docs/user/DESKTOP_GUIDE.md#data-and-troubleshooting). Remove keys and credentials before sharing logs or reporting issues.

## Result coverage

YTB-BOT focuses on new channels that meet the filters and have an email address or supported contact link in their public description. Results depend on keywords, search depth, and API quota. They do not represent the entire market or predict revenue or viral potential. Saved metrics do not refresh automatically over time.

Contact details have not been verified for deliverability. Gmail accepting a request does not guarantee delivery to the recipient.

## Development

The application uses React, TypeScript, Python, pywebview / Edge WebView2, and SQLite. Install Python 3.12, Node.js 22.12+, and npm, then run these commands in the project directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
npm ci --prefix frontend
npm run build --prefix frontend
python gui_app.py
```

Configure the API using [`.env.example`](.env.example). Testing, build, and operational instructions are available below:

| Document | Contents |
| --- | --- |
| [Development and testing](docs/engineering/DEVELOPMENT.md) | Environment, commands, and verification |
| [Architecture](docs/engineering/ARCHITECTURE.md) | Structure and component responsibilities |
| [Build and release](docs/engineering/RELEASE.md) | EXE packaging, CI, and updates |
| [Product direction](docs/product/COMMERCIALIZATION.md) | Scope and commercialization preparation |

## License

The source code is distributed under the [Apache License 2.0](LICENSE).
