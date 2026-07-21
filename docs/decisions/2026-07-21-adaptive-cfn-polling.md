# 2026-07-21: Adaptive CFN polling

## Context

The application polls the CFN battle log at a fixed configured interval even
when repeated successful responses contain no new matches. The configured
range is currently 5 to 90 seconds, while the CFN scraping note recommends at
least 90 seconds.

The current error path also collapses request failures, authentication errors,
WAF throttling, maintenance responses, and JSON failures into an empty match
list. The scheduler consequently records those failures as successful empty
fetches and clears its existing exponential backoff. In addition, browser
status polling can indirectly call CFN while the BuildID cache is empty.

The reported traceback is incomplete, so request frequency cannot be confirmed
as the exact cause. The polling lifecycle should nevertheless distinguish a
valid empty response from a failed response before adding idle throttling.

## Decisions

- Keep the persisted `poll_interval` as the normal interval and preserve its
  existing 5-to-90-second setting contract in this change.
- Treat only a successfully fetched and parsed battle log with no newly stored
  replay IDs as an empty fetch.
- After five consecutive real-CFN empty fetches, change the runtime polling
  interval to five minutes. Do not persist the five-minute runtime interval.
- Return automatically to the configured normal interval when a new match is
  found.
- Add a Dashboard action that returns idle polling to the configured normal
  interval. It resets only idle state and must not clear a rate-limit or error
  backoff. It schedules the next normal interval rather than performing a CFN
  request inside the HTTP request.
- Propagate expected CFN request, HTTP, authentication, maintenance, and JSON
  failures to the scheduler as classified errors. Preserve the existing
  30-minute maximum exponential error backoff, with a safe minimum based on a
  90-second normal cadence, and honor a numeric `Retry-After` value up to that
  maximum.
- Keep idle throttling and error backoff as separate runtime states. Errors do
  not increment or reset the empty-fetch counter, and the manual normal-mode
  action does not clear error state.
- Make `/api/status` and Dashboard rendering use cached scheduler
  authentication state. Rendering or refreshing a page must not itself make a
  CFN request.
- Expose normal interval, effective interval, mode, empty-fetch count, and the
  effective next-attempt time through the existing scheduler status object.
- Keep mock mode at the normal interval and isolated from idle throttling.

## Non-goals

- Do not change the persisted polling setting range in this slice.
- Do not add database schema or configuration migrations.
- Do not change CFN authentication credentials, routes unrelated to polling,
  Docker/CI/deployment behavior, ports, or external exposure.
- Do not access production data or make a live CFN request during verification.

## Verification

- Unit tests cover valid empty responses, idle transition, automatic and manual
  normal-mode restoration, separation from error backoff, classified CFN
  errors, and side-effect-free status rendering.
- Run `python -m pytest` and `git diff --check`.
