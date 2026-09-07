# AGENTS.md

This entry governs the SF6 logs dashboard and reporting service.

## Verified project facts and protected behavior
Preserve dashboard, report, settings, API, SSE, and OBS overlay URL contracts; CFN/Buckler request pacing, authentication, parsing safeguards, and mock isolation; scheduler lifecycle and idle/error backoff separation; SQLite compatibility; production match data, sessions, settings, and stored credentials; Docker amd64/arm64 support, Raspberry Pi runtime, port, restart policy, timezone, and persistent volume mapping. Do not alter tunnels, domains, image publication, deployment, credentials, production volumes, or exposure without explicit scope.

## Authority and scope
Apply runtime, tool, organization, and safety policy, then explicit user policy, then this entry and the approved task. Verified repository facts replace defaults; they do not grant authorization. Preserve unrelated work and stop on an overlap that requires guessing.

## Execution
Choose the smallest correct change. The user selects the runtime model and effort; role configuration owns model, effort, and role instructions. Use one bounded writer for settled work, adaptive implementation only for material native/platform uncertainty, and read-only exploration or review only when independently useful. Keep one writer for overlapping files. A changed candidate after review must be restabilized; after a second correction or two blocked returns, reset the contract before continuing. Persisted handoffs are for named cross-session, interruption-sensitive, risky, or separately executed work; otherwise use the approved inline scope. Optional cheap direct regression tests are appropriate when they materially support changed behavior; do not require a new harness or full suite by default.

## Safety
Do not inspect or edit secrets, credentials, local settings, runtime or production state, generated heavy artifacts, dependencies, CI/CD, deployment, publication, or external exposure unless explicitly in scope. Never reproduce private values. Do not commit, push, or publish unless explicitly requested. Report source readiness separately from unavailable runtime verification.

## Completion
Review the stable diff against every criterion and protected behavior, verify affected references and Markdown fences, run the smallest relevant checks plus git diff --check, and report changed files, evidence, blocked checks, partial edits, and unresolved questions.

## Checks
The available suite is python -m pytest. Runtime smoke on port 8510 requires isolated data and credentials because app.py starts the scheduler. Documentation-only work uses git diff --check and focused reference scans.
For incomplete delegated work, report the blocker, resume condition, and next owner/action. Requested model or effort is configuration context, not execution evidence; unknown stays unknown, with no diagnostic-only agents or probes to fill observation fields. After stable-diff review, read deeper only for gaps, conflicts, or concrete risk; rerun checks only for a mandatory contract, changed target or assumption, insufficient evidence, or integration risk. Return concise results and evidence references without raw logs or unchanged inventories. While children run, continue useful work within existing ownership and parallelism rules; otherwise wait for notifications. Avoid liveness-only polling, rereads, or state rewrites; respond to errors, inconsistent state, and user steering, and follow host progress rules.
