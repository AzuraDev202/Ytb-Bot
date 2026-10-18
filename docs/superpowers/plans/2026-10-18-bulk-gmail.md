# Bulk Gmail Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. The task details below retain the original implementation requirements; verified results are recorded at the end.

**Goal:** Review and send separate Gmail messages to deduplicated saved channel email groups, with durable per-recipient outcomes.

**Architecture:** Derive canonical groups from saved SQLite results. Persist an immutable reviewed batch, claim each sender/address before sending, and use one sequential background worker with a process-level lock. Expose the workflow through the existing desktop bridge and React Results workspace.

**Tech Stack:** Python 3.12, SQLite, Gmail REST API, React 19, TypeScript, existing pywebview bridge, unittest and Playwright.

**Spec:** The bulk workflow and limits in [Contact Composer](../../user/CONTACT_COMPOSER.md#bulk-gmail-across-saved-channels).

## Global Constraints

- No send occurs during selection or preparation; explicit review precedes start.
- Use existing OAuth identity and `gmail.send`; no inbox scope or automatic reconciliation.
- One separate message per normalized email; preserve distinct dot/plus aliases.
- Maximum 100 selected email groups per application batch; sequential requests with a two-second pause between sends. Neither value is a Gmail provider limit.
- Stop after the current request; never retry an uncertain send automatically.
- Persist recipient outcomes before advancing; accepted is not guaranteed delivery.
- Social groups are read-only in bulk mail. Preserve existing single-channel and social workflows.
- English, Vietnamese, and Simplified Chinese labels; canonical bridge keys remain English.
- No real channel addresses in tests; do not claim real OAuth or delivery verification from mocks.

## Review Focus

1. Same address across pages and scans: produce one recipient with all current channel associations.
2. Stop while Gmail is responding: retain its actual outcome and cancel only remaining recipients.
3. Process dies after submission: retain an unknown outcome and never resume automatically.
4. Repeated start or another process: at most one worker and no duplicate sender/address claim.
5. Invalid or social selection and changed sender: reject before any Gmail request.

## Verified provider research (2026-10-18)

Gmail accepts MIME content encoded as base64url in `raw`, submitted with `messages.send`. Reuse the existing single-recipient transport instead of a provider batch endpoint. [Google sending guide](https://developers.google.com/workspace/gmail/api/guides/sending).

API quota measures request units (`messages.send` currently costs 100 units). This differs from mailbox sending allowances; avoid hardcoding a daily remaining-mail estimate or interpreting an application batch cap as Google quota. [API usage limits](https://developers.google.com/workspace/gmail/api/reference/quota).

Google documents distinct authorization, rate, mailbox, concurrency, and server errors. Mailbox sending limits are shared across clients, and even a successful HTTP response cannot establish delivery. Google's generic retry/backoff guidance does not supply a send idempotency guarantee. Our engineering decision is to stop and persist uncertain side effects without automatic retries. [Gmail error handling](https://developers.google.com/workspace/gmail/api/guides/handle-errors).

Workspace account limits can differ for trial and paid accounts and can change; Google applies daily limits over a rolling period. Consult the current table rather than advertise one allowance for all senders. [Workspace sending limits](https://support.google.com/a/answer/166852) (the English direct fetch failed during research; the official Portuguese version was available at https://support.google.com/a/answer/166852?hl=pt).

Google's sender guidance covers authentication, reputation, accurate headers, opt-outs, and additional requirements for bulk traffic to personal Gmail accounts. The composer does not implement a subscription service or one-click unsubscribe infrastructure. [Email sender guidelines](https://support.google.com/mail/answer/81126).

## File responsibilities

| File | Responsibility |
| --- | --- |
| `ytb_bot/core/contact_groups.py` | Latest row per saved Channel ID; stable canonical contact groups |
| `ytb_bot/core/bulk_store.py` | Persist batches and unique sender/address claims |
| `ytb_bot/desktop/bulk.py` | Preparation validation, worker lock, pacing, stop, recovery |
| `ytb_bot/desktop/outreach.py` | Share duplicate protection with single mail |
| `ytb_bot/desktop/api.py` | Bridge, lifecycle/update protection |
| `frontend/src/components/ContactGroups.tsx` | Typed grouped-contact bridge data and selection |
| `frontend/src/components/BulkComposer.tsx` | Selection, immutable review, progress/history |
| `frontend/src/components/ResultsView.tsx` | Results entry and integration |
| `frontend/src/vi.json`, `frontend/src/zh-CN.ts` | Interface translations |
| `tests/test_bulk.py`, `frontend/tests/bulk.spec.ts` | Mocked backend and browser verification |

### Task 1: Canonical groups and durable batches

**Files:** Create `ytb_bot/core/contact_groups.py`, `ytb_bot/core/bulk_store.py`; test `tests/test_bulk.py`.

**Interfaces:** Produce `contact_groups(store) -> list[dict]`; groups contain `id`, `kind`, `value`, `channels`, `last_status`, `last_created`. Produce `BulkStore.create(payload)`, `get(batch_id=None)`, `list()`, `change(batch_id, callback)`, `attempted(sender, account_id)`, and `claim_contact(sender, recipient, source, account_id)`.

- Add tests proving latest saved row wins per Channel ID, case/whitespace email normalization, cross-channel grouping, and distinct plus/dot addresses.
- Run `python -m unittest discover -s tests -p test_bulk.py -v`; confirm new group/storage assertions fail before implementation.
- Implement grouping using all saved runs, validated contact extraction, stable group IDs, and grouped channel ID/name associations. Keep social groups distinct from email groups.
- Persist `bulk_batches(id, created, payload)` and unique `contact_claims(sender, recipient, created, source)` transactionally; include existing single-send attempts when deciding prior contact.
- Verify reopen persistence and two competing claim attempts yield exactly one success with the focused test command above.

### Task 2: Reviewed sequential worker and desktop bridge

**Files:** Create `ytb_bot/desktop/bulk.py`; modify `ytb_bot/desktop/outreach.py`, `ytb_bot/desktop/api.py`; test `tests/test_bulk.py`, `tests/test_bulk_bridge.py`, `tests/test_outreach.py`, `tests/test_react_backend.py`.

**Interfaces:** `BulkOutreach(outreach, interval=2)` provides `groups()`, `prepare(payload)`, `get(batch_id=None)`, `list()`, `start(batch_id)`, `stop(batch_id=None)`, and `is_running`. Preparation input contains `group_ids`, `account_id`, `subject`, `body`. Batches contain `id`, `created`, `account_id`, `sender`, `subject`, `body`, `recipients`, `status`, `error`; each recipient contains `email`, `channels`, `status`, `message_id`, `error`.

- Test invalid/social groups, more than 100 groups, repeated IDs, missing sender, subject injection, and sender disconnection before start; assert zero Gmail calls.
- Implement preparation with existing subject/body limits (200/50,000 characters), saved contact validation, and immutable sender/content snapshots. Preparing never invokes Gmail.
- Implement transactional draft-to-running transition and OS-owned worker lock. Claim each sender/address durably before transport; honor claims from single sends and prevent started-batch replay.
- Test two starts/process owners, prior single-mail attempts, two-second pacing using an injected short interval in tests, stop during an in-flight send, and stop during the pause.
- Persist recipient states `pending`, `sending`, `accepted`, `failed`, `unknown`, `skipped`, `canceled`; batch states `draft`, `running`, `completed`, `stopped`, `interrupted`, `error`. Stop the rest on errors; preserve actual outcome of the in-flight request.
- Test timeout and process restart after submission: sending becomes unknown, pending becomes canceled, no automatic resume/retry. Preserve an active worker owned by another process during recovery.
- Expose `contact_groups`, `get_mail_state`, `list_bulk_mail`, `prepare_bulk_mail`, `start_bulk_mail`, `stop_bulk_mail`, `get_bulk_mail`, and `set_bulk_dirty` bridge methods and include bulk activity in account, shutdown, and update guards without blocking read-only progress polling.
- Run the targeted unittest modules and require process exit code zero.

### Task 3: Results selection, review, progress, and translations

**Files:** Create `frontend/src/components/BulkComposer.tsx`; modify `frontend/src/api.ts`, `frontend/src/components/ResultsView.tsx`, locale files and `frontend/src/studio.css`; test `frontend/tests/bulk.spec.ts`.

**Interfaces:** Use Task 2's batch/group fields through typed bridge methods; never reconstruct recipients from a visible paginated table. Treat the prepared backend snapshot as review content.

- Add a mocked-bridge browser test selecting shared email groups, showing their associated channels, and rendering social groups without selectable email checkboxes.
- Implement **Grouped contacts** beside Scan history; **Compose bulk email**, **Preview batch**, **Send batch**, **Stop batch**, and **Batch history** actions; sender selection, subject/body fields, selection count, and clear cap/pacing copy. Preserve content across language switches and dirty-draft navigation guards.
- Render complete saved review before enabling explicit start. Changing content invalidates the review. Disable duplicate start while active; poll persisted batch progress and show each recipient outcome, stop, and prior batches.
- Add tests proving prepare sends nothing, start uses reviewed ID, stop invokes only the stop method, unknown/accepted copy avoids delivery claims, and narrow layouts remain usable.
- Translate new labels in all three languages using existing translation conventions; keep sender/address/user content unchanged.
- Run `npm run build --prefix frontend` and `npm test --prefix frontend`; require exit code zero.

### Task 4: Regression verification and user documentation

**Files:** Modify `README.md`, `docs/user/CONTACT_COMPOSER.md`; retain this plan.

**Interfaces:** Document final shipped labels and behaviors from Tasks 1?3, including provider references above.

- Verify existing single-channel drafts, send protection, social copy/open actions, saved Results, and account setup still work in mocked tests.
- Run `python -m unittest discover -s tests -v`, frontend build, and Playwright. Report environment-related failures separately from assertion failures; never describe planned commands as completed checks.
- Document exact entry, review/start/stop flow, persisted outcomes, sender/address duplicate suppression, app cap versus provider limits, no automatic retries, and manual Gmail Sent checks.
- Record actual commands/results in the implementation handoff. Real OAuth and delivery remain unverified unless separately exercised with a mailbox the user controls.

## Self-review

Coverage includes grouping, persisted claims/snapshots, explicit authorization boundary, sequential pacing, stop/recovery, bridge lifecycle guards, three languages, regression tests, and user/provider documentation. The five Review Focus cases belong to Tasks 1?3. Backend/frontend names must be reconciled with the final bridge before completing the implementation.


## Implementation handoff

Implemented canonical contact groups, immutable reviewed batches, transactional recipient claims shared with individual sends, a sequential Gmail worker, stop/restart recovery, desktop lifecycle guards, grouped Results, batch history, and three-language UI. The final UI bridge data types live beside ContactGroups and BulkComposer; the generic API wrapper and App did not need changes.

Independent safety review found a stopped batch could retain an orphaned sending recipient after native close. A regression test reproduced it, then recovery was extended to mark orphaned sending recipients unknown under the process lock, while preserving the stopped batch status.

Verification uses fake Gmail and a mocked browser bridge. Real mailbox OAuth, provider quota behavior, and delivery are not verified. See the final validation results below.

Final validation (2026-10-18):

- `python -m unittest discover -s tests -v`: 97 tests passed, exit 0, including Windows DPAPI and orphaned-send recovery.
- `npm run build --prefix frontend`: locale validation (242 keys), TypeScript, and production bundle passed, exit 0.
- `npm test --prefix frontend -- --reporter=line`: 20 browser tests passed, exit 0.
- `python scripts/checks/smoke_react.py`: native WebView2 bridge and three-language unsaved bulk draft close guards passed, exit 0.
- `git diff --check`: passed; only Git line-ending normalization notices.
