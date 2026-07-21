# Adaptive poll scheduler handoff

## Goal

After classified CFN errors exist, implement runtime idle slowdown and a safe
restore-normal scheduler operation. This slice does not change HTTP routes or
templates.

## Read before editing

- `AGENTS.md`
- `CLAUDE.md`
- `docs/decisions/2026-07-21-adaptive-cfn-polling.md`
- `services/cfn_scraper.py`
- `services/scheduler.py`
- `tests/test_core.py`

## Approved files

- `services/scheduler.py`
- `tests/test_core.py`

## Requirements

- Runtime constants: five consecutive valid empty real-CFN fetches and a
  300-second idle interval. Do not persist idle state.
- Track normal interval, effective interval, empty count, and idle slowdown
  under the existing status lock.
- Fifth real empty fetch enters idle and reschedules only `cfn_poll` to 300s.
- A newly inserted match restores the configured normal interval and clears
  idle state. Mock mode remains normal and does not accumulate empties.
- Classified and unexpected errors neither increment nor clear idle count and
  do not change the effective idle/normal interval.
- Catch `CfnFetchError`. Authentication errors mark `auth_ok=False` and retain
  the current auto-login attempt. Successful real fetches mark it true.
- Error backoff remains capped at 1800s and is calculated from at least a
  90-second base. A classified numeric `retry_after` may increase it up to the
  cap.
- `last_fetch` changes only for a valid completed fetch.
- Add `restore_normal_polling()`: clear idle state and reschedule to the stored
  normal interval without making a CFN request or clearing error/backoff state.
- Existing `update_poll_interval()` also clears idle state and applies the new
  normal interval.
- Extend status with normal/effective interval, empty count, idle boolean,
  `normal|idle|error` mode, and an ISO effective-next-attempt timestamp. Keep
  all old status keys.

## Tests

Use monkeypatch/fakes and reset module status between tests. Cover fifth-empty
idle entry, new-match restoration, mock isolation, classified-error backoff,
and manual restore preserving error state. Do not start the real scheduler,
touch `data/`, or contact CFN.

Run `python -m pytest` and `git diff --check`. Do not commit, push, or deploy.
