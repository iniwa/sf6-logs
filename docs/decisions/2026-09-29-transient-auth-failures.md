# Transient authentication probes and consecutive failure output

The observed history showed BuildID HTTP 502 followed by requests login 403
and browser login failure. A failed server probe does not establish cookie
expiry. Periodic authentication checks now retain their cached state and wait
for the next scheduled check on transport, non-auth HTTP, and parsing failures.
HTTP 401/403 and missing BuildID responses retain the existing recovery path.
Other BuildID callers retain the existing value-or-None contract.

Background poll, automatic-login, and BuildID exception output uses a threshold
of three consecutive failures of that operation. Earlier failures emit a brief
retry-wait message; success resets the count. Known network/HTTP failures still
need no traceback. Login requests falling back to the browser emit an informational
message: the overall background login result controls detailed failure output.
Manual login feedback, unexpected scheduler failures, and replay parsing are
outside this targeted change. Existing error status and safe recent history
remain available even for a single failure. No retry cadence, backoff, database,
URL, credential, image-platform, or persistent-volume contracts change.

Validation (2026-09-29): success. All 98 offline Python tests passed, including
transient/auth rejection separation, threshold/reset, retained history and
unchanged exponential backoff. An isolated temporary database with outbound
requests blocked passed six Flask route checks and three scheduler-job checks.
Independent read-only review found no blocking defects. Production application
is a separate verification step; these checks do not establish live CFN recovery.
