# Linked Accounts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Connect Gmail and Facebook Fanpages, submit reviewed Messenger messages automatically, select visible email groups, and remove successfully contacted channels from grouped contacts.

**Architecture:** Keep the React/Python desktop bridge and SQLite workspace. Reuse the Windows credential vault in a separate Facebook vault file, use Meta conversations for explicit recipient matching, and maintain durable send attempts and completed-channel exclusions. No public webhook service or new runtime dependency is required.

**Tech Stack:** Python standard library HTTPS, SQLite, existing CredentialVault, React 19, TypeScript, unittest and Playwright.

**Spec:** `docs/superpowers/specs/2026-10-19-linked-accounts-design.md` (approved by user on 2026-10-19).

## Global Constraints

- Initial social sending support is Facebook Fanpages, selected by the user.
- Never infer a recipient ID from a URL or name.
- Send only after the user reviews the sender, recipient and message and starts sending.
- Failed, canceled, skipped and unknown outcomes do not remove channels.
- Retain scan history and immutable send history.
- Mock external APIs; tests never send real messages or require live credentials.
- Live Facebook connection and actual message delivery require the user's Page credentials and Meta app permissions.
- Use existing locale catalogs for English, Vietnamese and Simplified Chinese.
- Work in the current checkout; leave unrelated files intact and do not automatically commit or deploy.

## Review Focus

- Shared email recipients: exclude exactly the channels in the accepted recipient snapshot; retain unrelated channels sharing an address later.
- Crashes between provider acceptance and completion: retain an uncertain attempt and prohibit automatic retries; reconcile persisted accepted history when reading the queue.
- Expired messaging windows and incomplete pagination: fail closed when the latest inbound message cannot be established.
- Tokens in upstream error messages or pagination links: return sanitized errors, use a fixed Meta host and bearer authorization, never follow arbitrary supplied URLs.
- Filter changes and 100 selected recipients: preserve hidden selections and represent partial visible selection accurately.

## File Responsibilities

- `ytb_bot/core/contact_completion.py`: persistent excluded channel IDs and reconciliation from accepted historical attempts.
- `ytb_bot/core/contact_groups.py`: apply completed-channel exclusions before grouping.
- `ytb_bot/desktop/outreach.py`, `bulk.py`: record completion following accepted Gmail submissions.
- `ytb_bot/desktop/facebook.py`: fixed-host Meta HTTP transport, Page validation and conversation eligibility.
- `ytb_bot/core/facebook_store.py`: explicit channel/Page/recipient bindings and immutable send attempts.
- `ytb_bot/desktop/facebook_outreach.py`: encrypted accounts, bindings, review snapshots and sends.
- `ytb_bot/desktop/api.py`: narrow bridge methods and coordination with update/send state.
- `frontend/src/components/LinkedAccounts.tsx`, `FacebookComposer.tsx`: account management and reviewed Facebook composition.
- `frontend/src/components/ContactGroups.tsx`: filtered select-all, account panel and per-channel Facebook composition.
- `frontend/src/vi.json`, `zh-CN.ts`, `studio.css`: localized copy and responsive styles.
- `tests/test_contact_completion.py`, `test_facebook.py`, `test_facebook_bridge.py`, `frontend/tests/linked-accounts.spec.ts`: behavior and integration verification.
- `docs/user/CONTACT_COMPOSER.md`: setup and operating instructions.

### Task 1: Select visible email groups

**Interfaces:** ContactGroups owns selection locally; existing `prepare_bulk_mail(payload)` retains its 1–100 email-group contract.

- [x] Add browser tests that filter contacts, select visible email groups, preserve off-filter selections, clear only visible selections, and assert the mixed checkbox state and 100-recipient cap.
- [x] Run `npm test --prefix frontend -- linked-accounts.spec.ts` and confirm the new select-all assertions fail.
- [x] Add a visible select-all checkbox using a ref for `indeterminate`; disable when loading or no visible email groups exist. Explain selection truncation at 100.
- [x] Add Vietnamese and Chinese translations and run the browser tests again.

### Task 2: Persist completed channels and reconcile Gmail history

**Interfaces:** `ContactCompletion(store).complete(channel_ids, source)` and `.completed_ids()`; `contact_groups(store)` excludes those IDs.

- [x] Write tests asserting accepted individual sends remove alternate contacts, accepted bulk recipients remove snapshot channels, failed/unknown sends retain channels, and exclusions survive restart and new scans.
- [x] Add tests for historical acceptance reconciliation, shared groups retaining unrelated channels, and replaying completion safely.
- [x] Run `python -m unittest discover -s tests -p test_contact_completion.py` and confirm failures before implementation.
- [x] Add an idempotent SQLite completion table and accepted-history reconciliation guarded by existing-table detection. Individual history excludes its channel ID; bulk history excludes recipient snapshot channel IDs.
- [x] Record successful completion after accepted status is durably persisted; keep provider status and cleanup errors distinct. Apply exclusions before constructing grouped contacts.
- [x] Run completion, outreach and bulk unittest modules; update existing assertions only when the approved queue behavior changes their expected result.

### Task 3: Page credentials, conversation eligibility and matching

**Interfaces:** `FacebookClient.page(token)`, `.conversations(token, page_id)`, `.recipient(token, page_id, recipient_id)` and `.send(token, page_id, recipient_id, body)`; `FacebookOutreach.state()`, `.connect(token)`, `.disconnect(page_id)`, `.conversations(page_id)` and `.bind(channel_id, page_id, conversation_id, recipient_id)`.

- [x] Write transport tests for Page identity validation, non-Page tokens, missing permissions, bounded fixed-host pagination, timeout sanitization and expired/incomplete inbound history.
- [x] Run `python -m unittest discover -s tests -p test_facebook.py` and confirm missing-module failures.
- [x] Implement injectable standard-library HTTPS transport against a pinned, currently supported Graph API version verified from official Meta documentation during implementation. Reject redirects; send bearer tokens in headers and paginate using validated cursors.
- [x] Add separate encrypted Page account storage using `CredentialVault`; public state exposes Page ID and name only. Validate messaging capability using a conversations request before accepting the connection.
- [x] Persist explicit recipient bindings after validating the saved channel has a Facebook contact and the participant belongs to the selected Page conversation. Require a two-party conversation and latest inbound message inside 24 hours; reject future timestamps and unverifiable history.
- [x] Run the tests again; ensure mocked tokens never appear in public state or errors.

### Task 4: Durable reviewed Messenger sends

**Interfaces:** `FacebookOutreach.prepare(channel_id, payload)` returns an immutable draft ID and review snapshot; `.send(draft_id)` returns attempt status and safe message; `.history(channel_id)` returns public attempts.

- [x] Add tests for stale bindings, disconnected Pages, changed review payload, duplicate submission, concurrent sends, accepted completion, rejected requests and unknown transport outcomes.
- [x] Verify tests fail before adding SQLite drafts/attempt claims and the send service.
- [x] Persist an immutable review snapshot containing Page, channel, recipient, conversation and body; bound body to Meta's documented text limit. Claim once transactionally before I/O and recheck eligibility immediately before submission.
- [x] Distinguish explicit API rejection from timeout/transport uncertainty. Record accepted only with validated response recipient and message ID; never automatically retry uncertain submissions.
- [x] Integrate DesktopAPI methods for state, connect/disconnect, conversations, binding, prepare/send/history. Coordinate sending with existing update and mail guards, restoring flags in `finally` blocks.
- [x] Run Facebook and bridge tests, including crash recovery and token sanitization checks.

### Task 5: Linked accounts and Facebook composition UI

**Interfaces:** LinkedAccounts refreshes public state; FacebookComposer accepts a channel ID and close callback, loads validated conversations, saves the explicit binding and prepares a review before submitting its draft ID.

- [x] Add browser mocks and tests for account connection errors, masked token input, token clearing after submit, disconnect, Page selection, explicit matching, expired eligibility, review and duplicate-send prevention.
- [x] Verify these tests fail before implementing the components.
- [x] Expose Gmail configuration/connect/disconnect and Page connect/disconnect in a grouped-contacts account panel. Poll existing Gmail connecting state with cleanup on unmount.
- [x] Add an accessible Facebook composer for each saved channel with a Facebook contact. Allow selecting a Page and conversation, explicitly linking the participant, composing, reviewing, sending and viewing history.
- [x] Keep reviewed content immutable during send, guard closing with unsaved text, and refresh grouped contacts after an accepted send. Preserve errors and unknown outcomes clearly.
- [x] Add responsive styles, Vietnamese and Chinese copy, and browser assertions for narrow-screen operation and keyboard labels.
- [x] Run `npm run build --prefix frontend` and the targeted Playwright tests.

### Task 6: Documentation and full verification

- [x] Document Page token generation, required permissions/app access, expiry/reconnection, manual channel matching, the 24-hour standard window, acceptance vs delivery, and cleanup of historical/shared-contact channels.
- [x] Run `python -m unittest discover -s tests`.
- [x] Run `npm run build --prefix frontend`.
- [x] Run `npm test --prefix frontend` with the existing Edge configuration; record environment blockers separately from assertions.
- [x] Run `git diff --check` and inspect the final changed files for secrets, unrelated modifications and inconsistent public bridge types.
- [x] Review the completed branch against the approved design; report automated checks and clearly state live Fanpage sending was not verified without user credentials.

## Execution Recommendation

Native execution in the current session: the shared SQLite completion and send-state contracts benefit from one implementer maintaining consistency. A fresh reviewer checks the completed change. Implementation is complete; verification evidence and rulings are recorded in the execution ledger.
