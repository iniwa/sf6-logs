# Polling status UI handoff

## Goal

Expose adaptive scheduler state without page-triggered CFN calls and add the
Dashboard restore-normal action after scheduler support exists.

## Read before editing

- `AGENTS.md`
- `CLAUDE.md`
- `docs/decisions/2026-07-21-adaptive-cfn-polling.md`
- `services/scheduler.py`
- `routes/api.py`
- `routes/dashboard.py`
- `routes/settings.py`
- `templates/dashboard.html`
- `tests/test_core.py`

## Approved files

- `routes/api.py`
- `routes/dashboard.py`
- `routes/settings.py`
- `templates/dashboard.html`
- `tests/test_core.py`

## Requirements

- Add `POST /settings/polling/normal`, call
  `scheduler.restore_normal_polling()`, and redirect to Dashboard. It must not
  call CFN.
- Dashboard Scheduler card shows mode, effective/normal seconds, effective next
  attempt, and concise last error. Only in idle mode show a button labeled
  `通常頻度に戻す`.
- Remove the unused live authentication call from Dashboard rendering.
- `/api/status` must return its existing boolean `authenticated` key using mock
  mode and cached scheduler `auth_ok`; it must not call
  `cfn_auth.is_authenticated()` or otherwise access CFN.
- Preserve existing route URLs and response keys.

## Tests

Register Blueprints in isolated Flask test apps without importing `app.py`.
Cover the POST service call/redirect and side-effect-free cached API status.

Run `python -m pytest` and `git diff --check`. Do not commit, push, deploy,
touch `data/`, or contact CFN.
