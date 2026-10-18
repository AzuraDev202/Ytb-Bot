# YTB-BOT Desktop User Guide

## Interface language

Use the desktop language selector to choose **English** (`en`), **Vietnamese** (`vi`), or **Simplified Chinese** (`zh-CN`). The selection is saved in local browser storage and native desktop preferences, and restored on the next launch. It takes effect without reloading the window; keyword edits and contact drafts remain open.

The setting changes interface text, native prompts, and application-authored messages. It does not translate channel data, user keywords, or draft content. Canonical result column identifiers and API field keys remain English regardless of the display language. The CLI and `--legacy` interface remain English. Button names in this guide use the English interface.

## Keywords in the application

1. Open **Keywords**, or select **Edit keyword table** on the discovery screen.
2. Edit cells directly, select **Add row**, or paste multiple lines from Excel into one cell. When pasting multiple columns, only the first column is used.
3. Select row checkboxes and choose **Delete** to remove rows; deletion requires confirmation.
4. Select **Save keywords**, or press **Ctrl+S** in the table, to save locally. **Use for scan** saves and returns to discovery.
5. Empty rows are ignored and duplicate keywords are combined when scanning. You can save an empty table.
6. If you close the application with unsaved changes, it asks for confirmation. Save before updating and restarting.

To import an older file, select **Import existing file**, open `.xlsx` or `.xls`, select a sheet/column, and choose **Import keyword column**. The application asks before replacing the list, reads the entire original column even when filtered, and places the data in the editor. Select **Save keywords** to keep it. The original file is not overwritten.

## Scanning and reviewing results

To contact a channel, choose **View full details â†’ Compose contact**. Gmail/Google Workspace supports direct sending through a connected OAuth account, with review, drafts, and send history. For Facebook and other social networks, copy your message and open the profile. Google setup and sending statuses are described in [Channel outreach](CONTACT_COMPOSER.md).

The React desktop automatically checks **Channel ID** against all scans in local storage, including saved results from completed, stopped, failed, and running scans. Each new scan accepts only channels absent from history; renaming a channel or changing keywords does not make an existing channel appear again. A channel that previously failed the filters can be accepted later if it meets the criteria. Existing history is retained. Deduplication covers storage on the current machine; external Excel results are not read automatically.

The application does not set `regionCode`, `relevanceLanguage`, or a channel-country filter. Channels from every country, including channels with no disclosed country, use the same age/views/contact filters. The **Country** column shows the channel's disclosed country code; missing data appears as **Not disclosed** (older scans may leave it blank).

This is keyword-based discovery across countries, not a complete list of all YouTube channels. Add keywords in multiple languages and increase depth to broaden results; API ranking, page limits, and quota still apply. `regionCode` filters video availability in a country, not the channel owner's nationality. See [YouTube search.list](https://developers.google.com/youtube/data/reference/rest/v3/search/list).

Enter an API key and filters, then select **Start discovery**. The active keyword list is saved before scanning. **Stop** waits for the current network request to finish and retains collected results.

Open **Results** or **View results in the bot** to review scans by time, status, and channel count. The table supports search, sorting, 100-row pagination, and copying checked rows. Full data is retained, including empty or failed scans; discovery shows a preview of only the first 200 channels.

Results are written to local storage in batches and when the scan ends; no `.xlsx` file is created. Select **Refresh** when viewing a scan still in progress. If the application closes unexpectedly, saved batches remain available; the request being processed may not yet have been recorded.

Shortcuts: `Ctrl+Enter` starts discovery, `Ctrl+O` imports a legacy file, and `Esc` closes filters or requests a stop. Normal `Ctrl+C` copies selected text; use **Copy** for checked rows.

## Data and troubleshooting

- Keyword tables and history: `%LOCALAPPDATA%/Ytb-Bot/data/workspace.sqlite3`. This is internal application data, not an Excel file for manual tracking.
- Close the application before backing up or transferring storage to another machine. Copy `workspace.sqlite3` to the same data directory on the destination machine.
- `.env` and `studio-settings.json` are beside the EXE, or at the project root when running from source.
- The new features do not delete or modify older Excel files.
- The API key is stored locally, used to call Google YouTube Data API, and not packaged into the EXE.
- Startup log: `%LOCALAPPDATA%/Ytb-Bot/logs/desktop.log`.
- In-app data management uses the default React interface. The CLI and `--legacy` are older tools retained for compatibility.

## Desktop updates

The application checks GitHub Releases after opening, every six hours, and when you select **Check for updates**. When an update is available, select **Update now** and confirm. The application downloads it, checks SHA-256, replaces the EXE, and reopens. Do not install updates during a scan.

The EXE compares SHA-256 even when the release has the same version, so it can receive a different build without a version increase. Running from source does not automatically replace Python. Older EXEs without this mechanism require one manual download.

The updater keeps the previous build as `<EXE name>.previous`. Its helper restores the old file if replacement or launch fails. If the new application opens but fails later, close it and restore `.previous` manually. Helper logs are at `%TEMP%/ytb-update-*/update-error.log`. SHA-256 checks integrity; it is not a Windows digital signature.

## Filtering channels with public contacts

New scans accept only channels meeting the age and views filters **and** containing an email address or specific contact URL in the channel description. The application recognizes email, Facebook, Instagram, LinkedIn, TikTok, X/Twitter, Telegram, Zalo, and WhatsApp. Merely mentioning a platform, linking its homepage, or using a share link does not qualify. The application does not verify ownership or whether the recorded address/link can be used to make contact.

In **Results**, the **Email**, **Facebook**, and **Other contacts** columns contain discovered information. Use **View full details** or **Copy** for the full content. Existing history remains unchanged; rescan to check contacts with the newer logic. Default scans continue saving inside the application and do not create Excel files.

The checked source is `snippet.description` from the [YouTube Data API](https://developers.google.com/youtube/data/reference/rest/v3/channels#snippet.description). Contacts found only in videos, banners, links outside the description, or sign-in-protected email sections are outside the current scope.
