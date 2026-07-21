# Adaptive CFN polling implementation handoff

## Goal

Implement one cohesive CFN polling lifecycle change: valid empty responses
eventually slow to a five-minute runtime cadence, new matches or a Dashboard
button restore the configured normal cadence, and real CFN failures reach the
scheduler's error backoff instead of masquerading as empty responses.

Read `AGENTS.md`, `CLAUDE.md`,
`docs/decisions/2026-07-21-adaptive-cfn-polling.md`, and all files listed below
before editing.

## Approved files

- `services/cfn_scraper.py`
- `services/cfn_auth.py`
- `services/scheduler.py`
- `routes/api.py`
- `routes/dashboard.py`
- `routes/settings.py`
- `templates/dashboard.html`
- `tests/test_core.py`

If another source file is required, stop and return the question to Codex.
Do not edit `README.md`; it has an unrelated pre-existing user change.

## Required behavior

### 1. Classify CFN fetch failures

- Add a lightweight typed exception in `services/cfn_scraper.py` for expected
  CFN fetch failures. It must carry a stable kind and may carry an HTTP status
  and numeric retry delay.
- A valid HTTP response that parses successfully continues to return
  `list[dict]`, including an empty list when the battle log genuinely contains
  no matches.
- Missing CFN user configuration, request timeout/connection failure, BuildID
  failure, 403, final 404 after the existing BuildID refresh, 405 WAF, 429,
  503/5xx, other HTTP failures, and JSON decoding failures must not return an
  empty list. Raise the classified exception instead.
- Treat 403 as an authentication kind and 405-with-WAF-header or 429 as a
  rate-limit kind. Parse only a non-negative integer `Retry-After` header; do
  not add date parsing or dependencies.
- Avoid duplicate full tracebacks for expected request/HTTP failures. Keep
  enough class/kind/status information in scheduler logs for diagnosis and do
  not log request headers, cookies, credentials, or CAPCOM/CFN user IDs.
- In `services/cfn_auth.py`, expected BuildID request failures should be logged
  concisely without a full traceback. Unexpected parsing/programming failures
  may retain traceback logging.

### 2. Separate normal, idle, and error state

- Add constants equivalent to five consecutive empty fetches and a 300-second
  idle interval. Do not persist these runtime values to SQLite.
- Track the configured normal interval, effective runtime interval,
  consecutive valid empty fetches, and whether idle slowdown is active under
  the existing status lock.
- A successful real-CFN fetch with zero newly inserted replay IDs increments
  the empty counter. On the fifth consecutive empty fetch, reschedule only the
  poll job to 300 seconds and mark idle slowdown active.
- A successful fetch with at least one new match clears the empty counter and
  restores the configured normal interval. Mock mode stays at the normal
  interval and does not accumulate idle empties.
- An error neither increments nor clears the empty counter and does not change
  the effective idle/normal interval.
- Preserve the existing maximum error backoff of 1800 seconds. Calculate error
  backoff from at least a 90-second normal cadence so a configured 5-second
  interval cannot retry errors every 10 seconds. A numeric `Retry-After` may
  increase the delay up to the same maximum.
- On an authentication-kind fetch error, mark cached authentication false and
  retain the existing auto-login attempt. On a successful real fetch, mark it
  true.
- `last_fetch` must represent a valid completed fetch, not a classified fetch
  failure.

### 3. Restore-normal operation and status

- Add `restore_normal_polling()` in `services/scheduler.py`. It clears the idle
  empty count/state and reschedules the poll job to the persisted configured
  normal interval.
- It must preserve `last_error`, `consecutive_errors`, and `next_retry_at` so a
  user cannot bypass WAF/error protection. It must not directly call CFN.
- Updating the saved normal interval through the existing settings action also
  clears idle state and applies the new normal interval.
- Extend `get_scheduler_status()` with stable fields for normal interval,
  effective interval, consecutive empty fetches, idle slowdown, and mode
  (`normal`, `idle`, or `error`). Keep existing fields for compatibility.
- Add an ISO timestamp for the effective next CFN attempt. During error
  backoff it must not claim an earlier scheduler tick as the next external
  attempt.

### 4. UI and read-only status paths

- Add `POST /settings/polling/normal` to call the restore operation and redirect
  to the Dashboard. Do not make an external request in the route.
- Update the Dashboard Scheduler card to show current mode and
  `effective interval / normal interval`. Show a Japanese-labeled
  `通常頻度に戻す` button only while idle slowdown is active. Display the
  effective next attempt and a concise last error when present.
- Remove the unused live `is_authenticated()` call from Dashboard rendering.
- Change `/api/status` to derive its boolean `authenticated` value from mock
  mode and cached scheduler status. The endpoint must not invoke CFN or call
  `cfn_auth.is_authenticated()`.
- Preserve all existing route URLs and response keys; adding scheduler status
  keys is allowed.

## Direct regression coverage

Add focused isolated tests without importing `app.py` or starting the real
scheduler/database.

- Five valid real empty fetches enter idle mode and reschedule to 300 seconds.
- A new match restores the configured normal interval.
- Mock empty fetches do not enter idle mode.
- Manual restore clears idle state but preserves active error backoff fields.
- At least network failure, 403, WAF/429 with numeric `Retry-After`, 503, and
  JSON failure are distinguishable from a valid empty list.
- The restore POST calls the scheduler service and redirects to Dashboard.
- `/api/status` returns a boolean cached authentication value without a live
  authentication call.

Reset module-level scheduler status in tests so order does not matter. Use
fakes/monkeypatches only; make no live CFN request and do not use `data/`.

## Non-goals and constraints

- No dependency, schema, configuration-range, deployment, Docker, CI/CD, port,
  domain, tunnel, or authentication-flow changes.
- No production data, local settings, `.env`, databases, credentials, runtime
  state, or live CFN access.
- Do not commit, push, deploy, or modify unrelated changes.

## Verification

Run:

```powershell
python -m pytest
git diff --check
```

Return changed files, behavior summary, exact verification results, unexpected
findings, and any design question. If a required behavior cannot be completed
within the approved files, stop and return it to Codex.
