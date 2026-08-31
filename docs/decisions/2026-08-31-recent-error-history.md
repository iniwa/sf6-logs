# 2026-08-31: Recent CFN error history

## Context

Adaptive polling is working, but intermittent errors can disappear from
Dashboard before the user can inspect them: a successful poll clears the
current `last_error`. Authentication helpers and per-replay parsing can also
fail and recover without leaving a polling error. The exact cause of the
reported intermittent failures is not yet established.

## Decision

- Keep current polling status semantics; add a separate history of the latest
  20 error events, newest first. Success and frequency changes do not erase it.
- Use a thread-safe process-local collector and copied snapshots. Restarting
  the application clears the history; no SQLite migration or settings change
  is needed. This does not recover events from before installation/restart.
- Capture polling, BuildID, periodic authentication, automatic/manual login,
  and individual replay-parse failures at their existing error boundaries.
  Distinct failed stages may produce distinct events even when the attempt
  eventually succeeds. Keep existing retry, fallback, return, and raise rules.
- Retain only timestamps, fixed source/category labels and summaries,
  exception class names, and validated HTTP status codes. Do not retain
  exception objects/messages, tracebacks, request/response content, or account
  and match data. Do not reuse the ordinary log buffer as the history source.
- Expose additive cached fields in the scheduler status and display them just
  below the Dashboard Scheduler row. Reuse its existing ten-second status
  polling, with escaped initial HTML and text-only dynamic rendering.

## Boundaries and verification

This is a diagnostic feature, not a fix for an unidentified CFN failure. It
does not change request frequency, authentication policy, scheduler lifecycle,
existing route contracts, database schema, dependencies, or deployment. It
does not sanitize all pre-existing console/current-status error output.

Tests use synthetic events and isolated Flask apps without starting `app.py`
or contacting CFN. They cover retention after success, recoverable failures,
bounded/concurrent snapshots, data minimization, API and HTML output, and the
existing polling/backoff behavior. Production application was a separately
authorized operations phase; its completed release and runtime checks are
recorded in the deployment handoff linked below.

## Verification evidence and limits

- 72 Python tests passed, including failure followed by success, authentication
  fallback, replay parse recovery, safe metadata access, and API/HTML output.
- `node tests/test_recent_errors_ui.js` passed without added packages; it
  checks text-only rendering, JST timestamps, empty/missing history, badges,
  and reuse of the single ten-second status timer.
- A real-app startup smoke used a fresh temporary DB, empty credentials,
  mock mode, and blocked outbound requests on loopback port 8510. Eight HTTP
  reads passed; all three scheduler jobs and the 90-second cadence remained
  intact, and a successful poll preserved history. Test processes were stopped.
- Independent review and text/syntax checks passed after the metadata-access
  correction. No production data, deployment configuration, or dependencies
  were changed.
- No browser was available for visual QA. Optional resume condition: once a
  browser connection is available, check populated/empty history and scrolling
  in an isolated instance with synthetic data. This needs no real credentials
  or deployment. Source/runtime checks above do not claim visual verification.

## Production application

The user subsequently approved publication and production application of
revision `b01833a1b51ad2b0ec0c3296145b5f7a9212d3ef`. Deployment and follow-up
runtime checks completed on 2026-08-31; see the
[archived operations record](../handoffs/archive/2026-08-31-recent-error-history-deployment.md).
The existing production data mount and deployment configuration were retained.
