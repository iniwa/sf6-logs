# Recent error history: production application

## Scope and outcome

- Route: `non-implementation` (operations); the primary owned the release,
  production application, and approval-sensitive decisions.
- The user explicitly approved production application and subsequently approved
  committing, pushing, and publishing the feature image.
- Production application and required runtime verification completed on
  2026-08-31. Final follow-up check: 10:33 JST.
- Published application revision:
  `b01833a1b51ad2b0ec0c3296145b5f7a9212d3ef`.
- The existing [Docker Build and Push run](https://github.com/iniwa/sf6-logs/actions/runs/33347395440)
  succeeded. The published manifest was checked for both `linux/amd64` and
  `linux/arm64`; the running production image is the arm64 image.

## Release isolation and application

- A feature-only release commit was prepared from the previously published main
  revision. The unrelated unpublished local policy commit, AGENTS.md edits,
  and README workflow edit were preserved and excluded from publication.
- Pushing to the existing Gitea origin synchronized the same revision to the
  existing GitHub release repository. No remote, mirror, or CI/CD configuration
  was changed.
- Read-only discovery located the existing Portainer stack definition. Its
  sole service matched the running container's actual data mount, port 8510,
  user, timezone, restart policy, and network.
- The immutable commit-tagged GHCR image was pulled and its revision and arm64
  architecture verified. The existing host Compose CLI applied it to the sole
  existing service using that stored definition, the original project
  directory, and the verified local image without another pull or build.
- The real writable bind mount at `/app/data` was retained. No repository
  example was substituted for the actual host path. Private deployment
  metadata is deliberately not copied into this record.
- The original image remains available for rollback. No volumes or images
  were deleted, and no credentials, local settings, database schema, ports,
  domains, authentication, or external exposure were changed.

## Verification correction

The first temporary operations smoke check used `scheduler.running` instead
of the existing API's `scheduler.is_running`. It therefore restored the
previous image despite the new application starting successfully. The primary
stopped that invalid verifier and independently confirmed that the old image
was running with the original runtime contract intact.

The checker was corrected, passed three isolated checks and a real read-only
check against the existing API, and received a fresh independent review.
The same unchanged application image was then successfully applied and
verified. No application-code correction was required.

## Final verification evidence

- Running image revision matches the feature commit above; runtime image ID:
  `sha256:5fd0aff8fd7b8ca776606ab5456cb2d5992a0da6e67f224b3723cdafe8f7d364`.
- Initial and follow-up checks confirmed the intended image, running state,
  and unchanged mount, port, network, user, timezone, command, and restart
  settings. Container restart count was zero at the follow-up check.
- Dashboard and `/api/status` returned HTTP 200, and a HEAD request to
  `/settings` returned HTTP 200. The scheduler reported `is_running: true`.
- The served dashboard contained the recent-error-history card. The cached
  status API included `recent_errors` and `recent_errors_limit: 20`.
- The stored Portainer stack definition still matched the pre-deployment
  fingerprint. Compose's container `config_files` label becomes `-` when the
  unchanged definition is supplied through stdin; the original project
  directory and stored `docker-compose.yml` remain usable and were rechecked.
- The feature-only release worktree passed all 72 Python tests, the standalone
  Node UI test, and whitespace checks before publication. Source review and
  isolated real-app checks are recorded in the implementation handoff.
- No live CFN error was induced or fetch forced. HTTP output was filtered to
  operational checks; credentials, match records, and error text were not
  exposed. Visual browser QA was unavailable and is not claimed.

## Completion and limits

The required release, application, review, and runtime follow-up are complete.
This record is archived. Subsequent documentation-only reconciliation does not
require a different application image.

History begins with events recorded after application startup, retains at most
20 events after successful polling/login, and clears on application restart.
It is diagnostic visibility, not a fix for the still-unidentified intermittent
CFN failure. Retention after success was verified with isolated synthetic
events rather than provoking an error in production.
