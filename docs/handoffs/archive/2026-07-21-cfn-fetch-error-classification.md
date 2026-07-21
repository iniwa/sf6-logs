# CFN fetch error classification handoff

## Goal

Make the CFN scraper return match lists only for valid parsed responses and
raise a classified expected exception for configuration, request, HTTP,
throttling, maintenance, and JSON failures. This slice does not change
scheduler or UI behavior.

## Read before editing

- `AGENTS.md`
- `CLAUDE.md`
- `docs/decisions/2026-07-21-adaptive-cfn-polling.md`
- `services/cfn_scraper.py`
- `services/cfn_auth.py`
- `tests/test_core.py`

## Approved files

- `services/cfn_scraper.py`
- `services/cfn_auth.py`
- `tests/test_core.py`

Do not edit any other file. `README.md` contains an unrelated user change.

## Requirements

- Define a lightweight `CfnFetchError` in `services/cfn_scraper.py` with a
  stable `kind`, optional `status_code`, and optional non-negative integer
  `retry_after`.
- Preserve `fetch_battle_log() -> list[dict]` for mock mode and successful real
  responses. A valid parsed battle log may return `[]`.
- Raise `CfnFetchError` rather than return `[]` for missing user ID, request
  failure, unavailable BuildID, 403, final 404 after the existing BuildID
  refresh, 405 carrying `x-amzn-waf-action`, 429, 503/other 5xx, any other HTTP
  failure, and JSON decoding failure.
- Use stable kinds including `configuration`, `network`, `auth`, `rate_limit`,
  `unavailable`, and `response` as applicable.
- Parse `Retry-After` only when it is an integer of zero or greater. Do not add
  date parsing or a dependency.
- Do not log request headers, cookie values, credentials, or CFN/CAPCOM user
  IDs. Avoid duplicate full tracebacks for expected request/HTTP failures.
- In `services/cfn_auth.py`, catch `requests.RequestException` separately in
  BuildID retrieval and log a concise error class without `exc_info=True`.
  Preserve traceback logging for unexpected parse/programming failures.
- Preserve the existing one-time BuildID refresh on 404 and all successful
  parsing behavior.

## Tests

Use fake responses/sessions only. Cover valid empty JSON, network failure, 403,
405 WAF or 429 with numeric `Retry-After`, 503, and JSON failure. Do not import
`app.py`, start the scheduler, touch `data/`, or contact CFN.

## Verification

Run `python -m pytest` and `git diff --check`. Do not commit, push, or deploy.
Return changed files and exact results. If another file is needed, stop and ask
Codex.
