# Project-wide Review — 2026-10-18

Scope: checkout `7367eba`, Python core/desktop/CLI/legacy, React, SQLite, Gmail/OAuth, updater, packaging, and CI. Combined perspectives: ECC production-audit, mattpocock code-review (behavior against documentation and code structure), and Superpowers requesting-code-review (independent review). No source changes, real email sends, or real YouTube calls.

## Findings requiring fixes

### 1. P2 — Draft loss when scan status changes
- Location: `frontend/src/components/ResultsView.tsx:51-67,86`; `ContactComposer.tsx:19,50,71`.
- While a scan is running, open outreach from history and enter unsaved content. When scanning completes/stops/fails, the `status` dependency reruns the effect; `setMeta(null)` unmounts WorkbookView and ContactComposer.
- Content held only in state is lost without confirmation; cleanup also clears Python's dirty flag.
- Suggested fix: keep the composer outside the table-loading lifecycle or retain the open table during refresh; protect drafts before every unmount. Add a regression for scan status changes while composing.
- Evidence: source path confirmed; no dedicated UI reproduction run for this scenario.

### 2. P2 — An older worker writes into a newer scan
- Location: `ytb_bot/core/engine.py:145-155`; `start` replaces `_run_id` and `_state`.
- Complete status is published before the worker reaches final persistence in finally. A new scan can start during this interval; the older worker uses the new shared `_run_id` and state.
- Deterministic reproduction using a trace to pause the worker before line 152 and block the second scan's factory: scan one remains running indefinitely in SQLite; the older worker also sets output=True for scan two.
- Suggested fix: finish persistence before publishing terminal status, or bind run_id/state locally to each worker and prevent start while the previous worker is alive.

### 3. P2 — Canceling window closure leaves the updater stuck
- Location: `ytb_bot/desktop/api.py:264-265`; `ytb_bot/desktop/app.py:41-49`; helper WaitForExit in `ytb_bot/updater.py`.
- Dirty state is checked only when download begins. Users can still edit keywords/compose mail during download. Afterward, the helper launches before window.destroy(); users can cancel closure at the unsaved-changes confirmation.
- destroy can be canceled in the installed pywebview. The helper waits 120 seconds and fails; the bridge does not receive the outcome and remains downloading, blocking scanning/updating until restart.
- Suggested fix: coordinate closure confirmation and helper startup; lock editing during installation or recheck and restore a recoverable state after cancellation.
- Evidence: application source and pywebview implementation; no actual EXE replacement performed.

### 4. P2 — Legacy interface loses partial results on API errors
- Location: `ytb_bot/legacy_ui/desktop.py:375-399`.
- Export sits at the end of a try block containing the entire scan loop. An API/network error on a later keyword skips export; finally only updates the interface. Found channels remain in RAM and are lost.
- Suggested fix: save incrementally or persist collected results on completion/error paths, while distinguishing scan errors from file-write errors.
- Evidence: control-flow analysis; the legacy GUI did not run successfully because of environment Tcl errors.

### 5. P2 — Public titles are exported as Excel formulas
- Location: `ytb_bot/cli/scanner.py:128-129`; `ytb_bot/legacy_ui/desktop.py:382-383`.
- External channel/video names are written directly with openpyxl. Values beginning with `=` become formulas instead of text.
- In-memory reproduction: `=HYPERLINK("https://example.invalid","Creator")` creates a cell with data_type `f`.
- Suggested fix: write untrusted text using an explicit string type and recheck the exported workbook. This finding does not apply to SQLite/React tables, which do not export Excel.

### 6. P2 — Two application instances can lose accounts or restore removed Gmail accounts
- Location: `ytb_bot/desktop/credential_vault.py:44-48`; `ytb_bot/desktop/outreach.py:64-68,102-111`.
- Locking applies only within one instance. Instance A reads the vault to refresh; instance B removes an account; A writes an older snapshot and restores the removed token. Both also share the same .tmp file and can race during replacement.
- Suggested fix: use an interprocess lock around the entire read-modify-write operation, or allow only one instance to use a vault.
- Evidence: analysis of cross-process write paths; two real instances were not run.

## Checks and limitations

- `npm run build --prefix frontend`: PASS; TypeScript and Vite builds succeeded.
- `npm test --prefix frontend`: all 13 tests printed `ok`; the runner hung after test results and was stopped with Ctrl+C (exit 1), so clean process completion was not confirmed.
- `python -m unittest discover -s tests`: 52 tests, FAILED with 8 errors. Errors involved Tk/Tcl initialization and one Windows credential encryption test; these are not automatically classified as product bugs. One test had several failing subtests, so the passed count cannot be inferred as 52-8.
- Separate updater review: 11/11 passed; separate release review: 4/4 passed, using dummy files and mocked launch operations.
- Real YouTube quota/API, real OAuth/Gmail, and real EXE updates were not verified. No safety certification or production-ready claim is made.
- No additional definite defects were found in workbook pagination/import, contact detection, or revision claiming before sending; this does not guarantee an absence of defects.

Priority: draft loss and the worker race; then updater and legacy/Excel data integrity; then cross-process credential vault synchronization.

## Remediation update — 2026-10-18

All six findings in this report were fixed:

- The history composer remains outside the table region replaced during reload; scan status changes or history errors do not lose drafts, and confirmation is retained before discarding changes.
- The scanner prevents a new scan from starting until the previous worker exits, including after status changes to complete.
- The updater launches its helper only after closure confirmations are accepted; canceled closure returns to a retryable state, and handoff errors keep the window open. The commit phase blocks sending and new dirty-state changes.
- Legacy saves collected results on API error paths as well; file-write failures are reported separately.
- CLI/legacy write formulas from public data as strings; exports use a temporary file and atomic replacement to preserve the old file if writing fails.
- The Gmail vault uses an interprocess lock for the full read-modify-write operation, bounded waiting, unique temporary files, fsync, and atomic replacement. Refresh does not overwrite removed accounts with an older snapshot.

Fix verification: 61/61 Python tests passed outside the sandbox (including real Tk/Tcl and Windows DPAPI); 14/14 Playwright tests passed and the runner exited cleanly; TypeScript/Vite build passed; real WebView2 smoke test passed (Gmail metadata bridge and unsaved/in-flight close guards). Regressions were added and failures observed before fixes; final cross-review found no new definite defects. No real email was sent, no real YouTube scan was run, and no real EXE was replaced. The existing EXE in dist had not been rebuilt from these changes.
