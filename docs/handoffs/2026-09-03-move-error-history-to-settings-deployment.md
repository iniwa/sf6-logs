# Move recent error history to Settings: production application

## Scope and status

- Route: `non-implementation` (release and operations).
- The source change is stable and the user explicitly approved committing,
  pushing, image publication, and application to the established production
  target. Production application is in progress.
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

## Remaining work

1. Publish the scoped implementation and documentation commit.
2. Verify the existing amd64/arm64 image publication for that exact revision.
3. Apply the immutable arm64 image through the verified production procedure.
4. Confirm the running revision, unchanged runtime contract, healthy routes,
   history API, and Settings-only card location without reading credentials or
   match records.
5. Record the result and archive this handoff only after follow-up succeeds.
