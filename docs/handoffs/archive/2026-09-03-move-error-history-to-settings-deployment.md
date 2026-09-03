# Move recent error history to Settings: production application

## Scope and status

- Route: `non-implementation` (release and operations).
- The source change is stable and the user explicitly approved committing,
  pushing, image publication, and application to the established production
  target. Production application is complete.
- Move only the `直近のエラー履歴` card from Dashboard to the bottom of
  Settings. Keep collection, retention, safe fields, the cached status API,
  and the existing ten-second UI refresh unchanged.

## Acceptance and safeguards

- Dashboard no longer contains the history card; Settings renders empty and
  populated history safely at initial load and continues updating it through
  the existing `/api/status` timer.
- Do not change CFN request pacing, scheduler jobs, authentication, database
  schema, dependencies, CI/CD, ports, external exposure, or production data.
- Use the verified existing multi-architecture publication flow and the stored
  Portainer stack. Preserve its actual data mount, service, network, user,
  timezone, and restart policy; retain the previous image for rollback.
- A production restart clears the process-local history by design. Do not
  provoke a CFN failure or force a fetch merely to repopulate it.

## Pre-release evidence

- All 72 Python tests passed, including route placement, populated/empty
  rendering, output escaping, and cached API behavior.
- The standalone Node UI behavior test, JavaScript syntax check, and
  `git diff --check` passed.
- The unrelated existing README workflow edit must remain unstaged and outside
  this release.

## Completion

- Published revision `e5584d690a6cf4be1f7b4d4af9d3b8f1c8e14397` through the
  existing [Docker Build and Push run](https://github.com/iniwa/sf6-logs/actions/runs/33700331254).
  The published manifest contains both `linux/amd64` and `linux/arm64`.
- Applied the immutable arm64 image to the sole existing service using the
  stored Portainer definition. Follow-up confirmed the intended revision, an
  unchanged runtime contract and stack fingerprint, and restart count zero.
- Dashboard, Settings, and `/api/status` returned HTTP 200; the scheduler was
  running and the safe history API remained available. The running image has
  the history card only in the Settings template, not Dashboard.
- The application restart cleared the four process-local history entries as
  documented. No CFN failure was induced and no fetch was forced.
- Browser discovery returned no available browser, so visual inspection is not
  claimed. Route tests, served-template checks, and HTTP/API checks establish
  the requested placement without reading credentials, match records, or raw
  error text.
- Required publication, application, rollback readiness, and follow-up checks
  are complete. This handoff is archived.
