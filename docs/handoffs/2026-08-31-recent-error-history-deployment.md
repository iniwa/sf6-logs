# Recent error history: production application

## Scope and status

- Route: `non-implementation` (operations); the primary owns deployment and
  approval-sensitive decisions.
- User requested production application of the completed recent-error-history
  feature. Application/restart of the established target is in scope.
- User explicitly approved commit, push, and image publication after the
  separate approval question. Production application is now in progress.
  Preserve the existing release path and exclude unrelated work.

## Verified evidence

- The source implementation has passed 72 Python tests, the standalone Node
  UI test, independent review, and an isolated runtime smoke. See the archived
  implementation handoff and the recent-error-history decision record.
- Read-only production access succeeded and identified exactly one running
  project container serving the existing port 8510.
- It uses the documented GHCR `latest` image, an existing writable bind mount
  at `/app/data`, and the `unless-stopped` restart policy. Exact private
  deployment metadata was inspected selectively and is not copied here.
- Repository README, compose file, and Docker publication workflow describe
  main-branch publication of amd64/arm64 images followed by pulling and
  recreating the existing production deployment. No repository update script
  was found. Gitea origin and the existing GitHub release repository have the
  same published main commit, also matching the current production image.
  Publish the feature-only commit to these established destinations and
  verify the existing GitHub workflow rather than changing CI/CD.
- The stored Portainer stack specification was located and rendered without
  changing it. Its sole service matches the running data mount, port, restart
  policy, timezone, and user. The existing host Compose CLI can recreate this
  service using the same specification and a verified, pre-pulled image.
- The repository's data-directory examples differ. Use the real existing
  mount unchanged; do not choose a repository example as a replacement.

## Resume conditions and remaining work

1. Approval received for committing/pushing the feature and publishing
   its image through the existing release path. Preserve unrelated AGENTS.md
   and README workflow edits, plus the pre-existing unpublished local commit;
   do not include unrelated work in a release by assumption.
2. Verify the Git/release destination and the actual existing container update
   procedure, keep a rollback reference, and confirm its port, restart,
   timezone, and data-mount configuration without reading credentials/data.
3. Publish only through the approved existing multi-architecture image flow,
   then apply the intended image through the verified production procedure.
   Do not change CI/CD, exposure, authentication, volume paths, or databases.
4. Check the running image and history UI/API support, original route health,
   and unchanged data-mount metadata. Do not deliberately trigger live CFN
   errors, force a fetch, expose response/error text, or read match records.
5. Record the actual deployment/verification result and archive this handoff
   only after all required runtime work is complete.
