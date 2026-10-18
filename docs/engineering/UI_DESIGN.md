# YTB-BOT Creator Studio: UI Design

The default interface is React + TypeScript in a pywebview / Edge WebView2 window. Python handles data; the separate CustomTkinter interface lives in `ytb_bot/legacy_ui/` and opens with `--legacy`.

## Design direction

- Graphite backgrounds in the dark theme and warm white in the light theme; one coral accent, with green reserved for statuses. No decorative gradients or sample metrics in the application.
- A compact metrics strip appears only on the scan screen: unique keywords, matching channels, processed topics, and elapsed time. Keyword/history screens prioritize table space.
- One primary action: **Start discovery**. Stopping and viewing results are secondary actions.
- Keywords use a directly editable table with add/delete/paste actions and an unsaved state.
- Results offer scan history, search, sorting, row selection, and pagination without downloading Excel.
- Segoe UI Variable/Segoe UI for body text, Bahnschrift for headings and metrics; use Windows system fonts without runtime font downloads. Metrics use tabular numerals.

Compact banners pair each screen title with a short task description. An inline SVG illustrates the channel-to-message flow and reveals once when the screen changes. Decorative artwork is hidden on narrower layouts to preserve working space.

Click feedback uses the Web Animations API without intercepting actions. Effects are short-lived and bounded, including inside modal dialogs. The Motion preference and system Reduce Motion setting disable decorative movement; labels, focus indicators, and send outcomes remain available.

## Interface languages

The main React desktop supports English (`en`), Vietnamese (`vi`), and Simplified Chinese (`zh-CN`) through a language selector. Persist the choice in browser-local storage and native preferences. Apply language changes in place without reloading or remounting editors, so unsaved keywords and contact drafts remain intact. Keep bootstrap/polling callbacks stable across language changes; changing display language must not reload saved keywords over an active edit.

Localization covers interface text, native prompts, and application-authored messages. Preserve channel data, user keywords, and draft content. Canonical column identifiers and API field keys stay English. The compatibility CLI and CustomTkinter interface remain English. This describes the intended behavior; release verification must include switching languages with unsaved content.

## Structure

| Path | Responsibility |
| --- | --- |
| `frontend/src/App.tsx` | Main screens and UI state |
| `frontend/src/components/ConfirmDialog.tsx` | Action confirmation dialogs |
| `frontend/src/components/KeywordTable.tsx` | Editable keyword table |
| `frontend/src/components/ResultsView.tsx` | Scan selection and history |
| `frontend/src/components/WorkbookView.tsx` | Results table / legacy Excel reader |
| `frontend/src/api.ts` | Data types and bridge contract |
| `frontend/src/styles.css` | Shared controls and layout |
| `frontend/src/studio.css` | Graphite/coral tokens, studio layout, and laptop adjustments |
| `frontend/src/components/WorkspaceHeading.tsx` | Screen-specific banners, illustrations, and statuses |
| `frontend/src/components/InteractionFeedback.tsx` | Short click feedback that respects motion preferences |
| `frontend/src/components/ContactGroups.tsx` | Grouped contacts, selection, filtering, and batch history |
| `frontend/src/components/BulkComposer.tsx` | Reviewed bulk-email drafts and recipient outcomes |
| `frontend/src/components/ScanSummary.tsx` | Actual scan metrics strip |
| `frontend/src/components/TableLoading.tsx` | Table-loading skeleton without fabricated data |
| `ytb_bot/desktop/app.py` | Native window, positioning, and lifecycle |
| `ytb_bot/desktop/api.py` | Bridge, file dialogs, and updates |
| `ytb_bot/core/` | Background scanning, table processing, and SQLite storage |

## States and interactions

Validation errors appear beside the affected field. The API key is masked by default; it is used for Google YouTube API requests and redacted from scan errors.

Filters become a menu below 840 CSS pixels; a closed menu cannot receive focus. When open, focus stays inside the menu; Esc closes it and returns focus to its trigger. Background content uses inert. A skip link leads to the main content. Content regions scroll. Tests check that the start button remains visible at 1280 x 720 and 1024 x 768. Theme and motion preferences are stored locally; effects respect reduced motion.

Tables show loading skeletons, inline errors, and retry buttons. Adding a row focuses the new cell. Logs scroll only inside their own region, without pulling the page to the bottom. Confirmation dialogs have dedicated accessible names and descriptions.

**Stop** waits for the current network request and then saves collected results. The network timeout is 20 seconds per request, not a limit for the entire scan.

Shortcuts and Excel operations are documented in the [desktop guide](../user/DESKTOP_GUIDE.md). Use **Copy** for rows selected by checkbox. Keyword imports always read the original column, even when the table is filtered. Table edits remain in a draft across screen changes and are saved only by Save/Use for scan or starting a scan. Closing with an unsaved draft requires confirmation; the native handler does not wait for JavaScript on the GUI thread.

## Visual checks

The results table stays within the workspace width and scrolls horizontally on its own. Left/right buttons below it reveal later columns; the selection column and **View full details** action stay on the left. Long URLs and titles are truncated in cells with tooltips. **View full details** opens every field in a row with wrapping, copyable text. Original data and copied rows are not truncated. Regression checks use all 10 columns, long URLs/titles, and 1280, 800, and 375px windows; screenshots are saved at `artifacts/ui/results-wide.png` and `result-details.png`.

```powershell
npm test --prefix frontend
python scripts/checks/smoke_react.py
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/checks/smoke_desktop.ps1
```

Playwright creates `artifacts/ui/react-dark.png`, `react-light.png`, `react-compact.png`, `studio-laptop.png`, `keyword-editor.png`, and `result-history.png`. Checks cover keyboard interaction, screen switching, error/empty states, retry, and text contrast in primary buttons/menus/logs across both themes (at least 4.5:1). This is not accessibility certification for the entire application. Bridge fixtures exist only in tests; product screens do not use fake data. The React smoke test checks real WebView2, visible HWND state, bridge arguments, and canceled closure with an unsaved table. The EXE smoke test checks the packaged application when its launcher requests Hidden, guarding against background-only startup regressions.

To capture the fallback interface: `python scripts/dev/preview_legacy_ui.py --output artifacts/ui/legacy.png`. This tool uses sample data without calling YouTube. Legacy tests must use the actual `CTk.mainloop()`, because `update()` alone can hide window initialization errors.

## Design references

Taste Skill (redesign-existing-projects) was used to review typography, colors, and unnecessary details. UI/UX Pro Max returned a Data-Dense Dashboard direction and keyboard focus guidance; its accompanying Enterprise Gateway/landing template and GSAP animations do not apply to this desktop application. mattpocock-skills:codebase-design was used to separate headings, metrics, and loading states into components with clear responsibilities. Keep the current React/CSS/Lucide stack to avoid new libraries or network resources.
