# Execution ledger: 2026-10-19-linked-accounts.md

Design and plan approved by user. Execute inline, with a final independent review.

Ruling: Use the current checkout on a feature branch as authorized in the plan; do not create a second worktree or commit automatically.

Pre-flight: completion service is shared by Gmail, Messenger and contact grouping; reconcile accepted immutable snapshots rather than mutable current addresses. Facebook bridge and UI consume Page IDs and server-owned review draft IDs, never accept tokens back from public state. Existing email bulk selection stays capped at 100.

Tasks: selection; completion; Facebook client/accounts; durable sends/bridge; UI; documentation and full verification.

Task 1: complete — visible selection, mixed state, filter preservation and 100 cap verified in Edge.
Task 2: complete — historical acceptance reconciliation and persistent per-channel exclusions; four completion tests passed. Ruling: reconcile when reading grouped contacts rather than introduce a crash-prone extra write after provider acceptance. Immutable history is the recovery source.
Task 3: complete — fixed-host HTTP client, bounded cursor pagination, encrypted Page accounts and verified conversation bindings. Ruling: pin v25.0 conservatively; Meta's direct version pages returned HTTP 429 during research, so live API/version validation remains part of the credential-dependent setup check.
Task 4: complete — immutable review snapshots, SQL unique recipient claims, eligibility revalidation, safe failure/unknown outcomes and update/shutdown guards. New regression tests were observed failing and then passing for stale clocks and concurrent rebinding.
Task 5: complete — Linked accounts and Messenger composer, explicit review, unsaved-change handling and translated copy. Four targeted Edge tests passed, including narrow layout and uncertain submissions.
Task 6: in progress — documentation updated. Initial full run passed 118 backend tests; subsequent transport coverage adds three cases. Initial browser run passed 25/27; the two failures were test-selector issues, corrected and confirmed in the four-test focused rerun. Final full checks follow.

Independent review: two important findings (stale eligibility clock, unlocked binding updates) fixed with regression tests; follow-up found no remaining important issues. The reviewer independently ran 20 Facebook service/bridge tests successfully.

Ruling: run Windows DPAPI/Tcl and Edge suites with approved elevated execution because the sandbox prevents their normal operation/teardown. The elevated backend run verified the native checks successfully; do not treat initial sandbox environment failures as application regressions.


Task 6: complete.

Final verification:
- `python -m unittest discover -s tests`: 124 passed (34.737 s), including Windows DPAPI and native GUI checks.
- `npm test --prefix frontend -- --reporter=line --timeout=30000`: 27 passed (54.3 s), Edge.
- `npm run build --prefix frontend`: passed; 268 required translation keys validated, TypeScript checked, production assets generated.
- `git diff --check`: passed (Git printed only line-ending normalization notices).
- New Python modules compiled successfully with compileall.
- Inspected the narrow Messenger composer screenshot from Playwright; no horizontal overflow or clipped actions.

A prior full browser run was interrupted by Vite reloading a page while source translations were being edited. The final run used fixed source and passed all tests; no unrelated pagination code was changed.

Live Gmail/Fanpage authentication and actual external delivery were not exercised. No live credentials were supplied and no messages were sent by tests. Page permissions, account setup and delivery require a user-controlled live check.

Completion: retain branch `feat-linked-accounts` and all changes for user review, as authorized by the plan; no commit, merge, push or deployment. No execution workspace was created outside the checkout.
