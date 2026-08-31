# Recent CFN error history

## Status and route

- Complete through primary recovery and final review; initial route: `bounded`.
- The primary owns design, documentation, verification setup, and acceptance.
- One native `bounded_implementer` owns the cohesive collector, CFN hooks,
  Dashboard rendering, and direct regression tests listed below.
- Do not commit, push, publish, or deploy. No runtime deployment is required
  for this implementation handoff.

## User goal and evidence

The user cannot follow intermittent console tracebacks and requests a recent
error history that remains visible after a later successful fetch.

Read `AGENTS.md`, `CLAUDE.md`, `README.md`, `app.py`, `config.py`,
`docs/cfn-scraping.md`, and
`docs/decisions/2026-07-21-adaptive-cfn-polling.md`, then the approved code and
relevant tests. The primary inspected these sources and the existing polling
handoffs. Current facts:

- `_poll_job()` clears `last_error` on success; keep that current-state contract.
- `_try_auto_login()`, `get_build_id()`, the requests-login fallback, and
  per-replay parsing can report failures independently of `last_error`.
- `_check_auth_job()` can raise outside the polling error handler.
- Dashboard and `/api/status` use cached scheduler state. `common.js` already
  requests `/api/status` every ten seconds.
- Existing ordinary logs can contain exception text and must not become the
  history data source.

## Writer ownership

- New `services/error_history.py`.
- `services/scheduler.py`, `services/cfn_auth.py`, `services/cfn_scraper.py`:
  narrowly scoped history hooks only.
- `routes/settings.py`: record a final login-test failure, preserving redirect
  and login behavior. No other settings changes.
- `templates/dashboard.html`, optional new
  `templates/partials/recent_errors.html`, and `static/js/common.js`.
- New `tests/test_error_history.py`; small necessary test-isolation adjustments
  to `tests/test_core.py` are allowed, but preserve existing coverage.
- Do not edit README or other documentation; the primary owns those files.

You are not alone in the worktree. Preserve the pre-existing README edit and
all unrelated changes; do not revert or stage other work. Return design
questions before expanding this boundary.

## Settled design

1. Keep the newest 20 events in a process-local bounded deque with a dedicated
   lock. A getter returns a new list and copied event dictionaries, newest
   first. No database, settings, file persistence, or new dependency. Success,
   idle transitions, manual frequency restoration, and mock-mode changes do
   not clear history. Process restart clears it.
2. Store only a JST ISO timestamp, fixed source code/label, normalized error
   kind, fixed safe summary, exception class name when available, and validated
   integer HTTP status when available. Never store `str(error)`, traceback
   text, exception objects, requests/responses, URLs, headers, bodies, replay
   IDs, account/player data, or arbitrary caller-provided messages. Unknown
   sources/kinds fall back to a fixed generic value. Bound/validate exception
   class names as identifier-like text. No attempt at blacklist-based redaction.
3. Preserve existing `CfnFetchError.kind` classifications. For other errors,
   recognize HTTP 401/403, 429, and 5xx and requests network exceptions where
   practical. Parsing sites explicitly use a response/parse kind and 2FA uses
   a distinct kind. HTTP status extraction must not rely on the truth value
   of `requests.Response` (error responses are falsey). Unknown exceptions
   remain unexpected rather than guessing their cause from exception text.
4. Add record calls at these boundaries:
   - scheduler `_record_poll_error()` for expected/unexpected poll failures;
   - scheduler `_try_auto_login()` for final failure and 2FA;
   - scheduler `_check_auth_job()` for uncaught errors: record then re-raise,
     preserving the existing APScheduler failure behavior;
   - auth `get_build_id()` for missing data/build ID and caught request/parse
     failures, without changing return values, cache rules, or requests;
   - auth `auto_login()` requests exception path before fallback (including
     invalid-credential failures). Final outcomes stay with their existing
     caller. Keep fallback and 2FA behavior unchanged;
   - scraper per-replay parse failure, even when the overall fetch succeeds;
     guard the existing replay-ID logging lookup for non-dict malformed rows
     so the error handler itself does not fail;
   - settings login-test catch for the final failure, including 2FA.
   Distinct failed stages of the same attempt may create separate events.
   Missing credentials by themselves are not a new scheduled failure event.
5. Add `recent_errors` and the history limit to `get_scheduler_status()` after
   releasing scheduler locks. Existing Dashboard and `/api/status` consume
   these additive fields without route or network changes. Keep `last_error`,
   counters, backoff, auth state, mock behavior, and scheduler jobs unchanged.
6. Show an always-findable card titled `直近のエラー履歴` immediately below the
   Scheduler/Activity Calendar row. Show newest-first timestamp (JST, including
   seconds), source, safe summary/kind, exception type, and HTTP code when
   present. Use a scrollable area if needed for 20 rows. Show an explicit empty
   state. Explain the 20-event limit, retention after success, clearing at app
   restart, and ten-second display refresh. Do not imply that past failures
   are still active.
7. Server-render initial history; reuse the existing ten-second `updateStatus`
   callback for live history refresh. No new timer, API endpoint, CFN request,
   or forced poll. Use DOM text APIs (`textContent`) for dynamic event fields,
   Jinja escaping for initial display, and do nothing on pages without the
   history card. Keep existing status badges and other scripts working.

## Constraints and non-goals

- No real CFN calls, live credentials, production/local settings, `data/`, DBs,
  container/volume changes, dependency manifests, build tooling, or deployment.
- Do not import `app.py` for tests: it starts the scheduler and initializes DB.
- Preserve route URLs, API fields, SSE/overlays, database compatibility,
  authentication flow, request pacing and backoff. This is diagnostics, not a
  retry or authentication-policy fix and not a general console-log viewer.
- Existing ordinary logs and current `last_error` text are outside the new
  safe history's data source and must not be copied into its payload.

## Acceptance and verification

- Error then successful poll clears only current error/backoff, retaining the
  event; further successes do not append error events.
- History survives normal-frequency restore and auth success; failed login
  followed by successful fallback and malformed replay followed by otherwise
  successful fetch are still represented.
- Expected HTTP/network, unexpected polling, BuildID failures, auth-check
  exceptions, 2FA/final auto-login failure, and manual login-test failure are
  recorded without altering existing returns, raises, or request counts.
- Verify newest-first order, 20-event cap, safe copies, empty state, and
  concurrent recording/snapshotting. Isolate collector and scheduler state in
  tests; use only synthetic data and mocked network/storage.
- Verify secret-shaped synthetic exception strings/URLs/headers/bodies never
  enter history/API history or initial/dynamic history markup; do not expose
  full legacy status as if it had been newly sanitized.
- Flask Blueprint tests use isolated apps, not `app.py`; check additive API
  fields and no CFN activity on status reads, plus initial populated/empty
  HTML and escaping. Cover the JS update behavior with an isolated local
  check if available without adding dependencies.
- Baseline `py -3.11 -m pytest -q`: 24 passed, 6 skipped because Flask is not
  installed in that interpreter. The primary is preparing isolated test
  dependencies so final Flask checks must not remain skipped.
- Run the full suite and `git diff --check`. No live smoke against production.

## Stable return gate

Before returning, self-review the stable diff against the constraints, report
test evidence and any gaps, then stop editing. The primary will integrate and
request an independent review only after this gate. A candidate changed after
review begins needs acceptance to be re-established. Do not mark complete if
any acceptance criterion remains unimplemented; report the bounded remainder.

## First return and resume condition

The first return supplied the collector, recording hooks, initial/live UI, and
three collector tests (33 tests passed including the 30-test baseline). The
diff is usable but not yet accepted: the principal error-then-success behavior
and recording integrations have no new regression coverage, HTTPError objects
are classified as network errors before inspecting their status, the initial
HTML lacks seconds/JST, and the auth-check guard misses its initial operations.
Resume the same bounded slice to correct those specific issues and implement
the already-agreed integration/UI checks. No final independent review has
started. Re-establish the stable return gate before review.

## Contract reset: regression coverage

The correction return addressed the identified code issues and still passed
33 tests, but explicitly left the agreed integration/retention/UI regression
coverage unimplemented. This is a second partial return, so the delegated
implementation contract is closed as interrupted, not accepted. The collector
and hooks remain usable candidate work. No review has started and no runtime
deployment occurred.

The primary now owns the candidate and the narrow remaining test/verification
slice: prove success retention, capture at the existing CFN/auth boundaries,
safe additive API/HTML output and dynamic rendering without live data or CFN
access. Production behavior should change only if these checks find a concrete
defect. Re-establish a stable self-review gate with this evidence before final
review. Browser discovery returned no available browser; visual inspection is
deferred, with HTML and JS behavior checks used for source acceptance.

## Stable candidate and final review boundary

The primary added offline integration coverage and reproduced/fixed missing
HTTP metadata on BuildID parse failures, invalid status metadata causing a
secondary exception, and the absent live JST label. All 68 Python tests and
the standalone Node UI behavior test now pass. History timestamps and deque
insertion share the same lock; source/kind/status normalization precedes
classification. The candidate is stable for final review.

The final `bounded_reviewer` is read-only. Review the changed services,
settings catch, Dashboard template, common.js and new tests against the
settled contract. Concrete material risks are credential/request content
entering the new retained API/HTML history, a recording hook changing failure
or recovery/backoff behavior, and rendering adding CFN requests or breaking
the existing status callback. Verify snapshot isolation and retention after
success as part of those risks. Existing ordinary log/current-status text is
not a sanitized part of this feature. Do not inspect production data or make
live requests; preserve unrelated AGENTS.md/README changes. Return actionable
findings or an explicit no-findings review with verification limits.

## Review correction and renewed stable gate

The first independent review found that an exception's metadata property
could itself raise while history was being recorded, interrupting the
auto-login failure handler. The primary reproduced that changed behavior in
the real `_try_auto_login()` boundary, plus a response-status accessor case.
Metadata access now falls back safely without inspecting exception text.
All four new regressions pass, the full Python suite passes 72 tests, and the
Node UI checks still pass. This is a new stable candidate for a bounded final
recheck of the reported issue and its effect on the collector.

An isolated real-app startup smoke on loopback port 8510 also passed: eight
HTTP reads, error then successful poll with retained history, unchanged
90-second cadence, all three scheduler jobs present, and no outbound CFN
attempts. It used a fresh temporary SQLite DB, no credentials, and a blocked
requests client; the server and scheduler were stopped afterwards. Visual
browser inspection remains unavailable, and production deployment is outside
this task.

## Completion

The bounded re-review found no remaining material issue in the corrected
collector or the previously reviewed history, capture, and rendering paths.
The final 72-test Python suite, standalone Node UI checks, JS syntax check,
text whitespace check, and repeated isolated runtime smoke all passed.
Required implementation and verification are complete; browser visual QA
was not available and is recorded as an optional follow-up in the decision
record, not claimed as verified. No production changes, staging, commit, push,
or deployment were performed. The unrelated AGENTS.md change, README workflow
edit, and existing local commit were preserved.
