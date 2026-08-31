# AGENTS.md

## Purpose

This is the Codex-side working agreement for `sf6-logs`. It records durable
product and data constraints, model and handoff policy, review rules, and
documentation lifecycle. `CLAUDE.md` contains compatibility boundaries for Claude-oriented tooling.

## Project

`sf6-logs` is a Street Fighter 6 statistics tracker and OBS overlay service. A
Python Flask application polls CFN/Buckler data, stores match and configuration
state in SQLite, and renders dashboards, reports, settings, APIs, SSE updates,
and Jinja/vanilla-JavaScript overlays. It is Docker-capable and runs on a
Raspberry Pi while retaining the existing multi-architecture image flow.

Before substantial work, read `README.md`, `app.py`, `config.py`, relevant
routes and services, affected tests, and current records under `docs/`.
Shared generation sources are under `D:/Git/CLAUDEmdStrage/_base/`; this
project uses the common sources plus the Windows, Docker, and Web profiles.

## Instruction Precedence

When instructions conflict, apply them in this order:

1. Runtime, tool, organization, and safety policy.
2. Explicit user instructions that change project policy.
3. Durable project instructions.
4. Other instructions for the current user task and the approved task scope.

The active handoff or equivalent inline prompt is the approved task scope.
Verified project facts override shared-source defaults. Only an explicit user
instruction to change project policy may revise a durable project rule; other
task instructions and approved scopes may narrow durable rules but may not
weaken them. Report unresolved conflicts instead of guessing.

- Prefer the smallest correct change and reuse existing capabilities before adding dependencies or parallel policy.
- Approvals and completion require concise, evidence-backed scope, verification, and residual-risk/blocked-check reporting.

## Model and Role Policy

- Before implementation, classify the initial route from acceptance evidence: `small-primary` for small or transfer-negative work, `bounded` for settled multi-step work with one verifiable writer, `adaptive` when unresolved native, platform, runtime, or cross-subsystem behavior is material, or `non-implementation` for analysis, design, review, or operations. This classification does not force delegation; reclassify only after a material scope change or contract reset.
- Use GPT-5.6 Sol as the preferred main worker; the user's actual runtime model and reasoning choice remains authoritative. Sol owns intent, design, approval boundaries, integration, and user communication and can directly finish small or transfer-negative work. Use configured Luna roles (`bounded_explorer`/`bounded_implementer`) for bounded work and Terra roles (`adaptive_implementer`/`bounded_reviewer`) for adaptive implementation or risk-justified review; do not force delegation or pin the main reasoning level in project instructions.
- Use native Codex roles: `bounded_implementer` is the cohesive default for settled work; choose `adaptive_implementer` directly when acceptance depends on unresolved native, platform, or cross-layer lifecycle behavior.
- Use `bounded_explorer` only for genuinely independent read-only questions and `bounded_reviewer` only when concrete correctness, security, compatibility, or verification risk warrants it. One active writer owns overlapping files or behavior.
- The writer's stable self-review gate is a dispatch barrier. If the writer changes the candidate after review starts, acceptance must be re-established; request a fresh final review only when material risk still warrants it. A second correction round, or two blocked/partial returns, requires a contract reset before continuing. If a selected role is unavailable or unobservable, use an observable equivalent or keep the work in the primary context.
- Name the concrete material risk in any reviewer handoff. Use a fresh task boundary for an independent phase with its own acceptance and verification; reintegrate delegated work from the stable diff and evidence instead of repeating its discovery.
- Claude Code is not an approved route unless an explicit policy change says so.
## Durable Project Rules

- Preserve the existing dashboard, report, settings, API, SSE, and OBS overlay
  routes and their documented URL contracts.
- Treat CFN/Buckler behavior as an external integration. Preserve request
  pacing, authentication handling, parsing safeguards, and mock/test isolation;
  do not increase live request frequency casually.
- Preserve the scheduler lifecycle, its CFN polling, authentication, and
  session jobs, and the separation between idle slowdown and error backoff.
- Preserve SQLite compatibility unless an explicit migration is designed and
  verified. Production match data, sessions, settings, and stored credentials
  are user data, not disposable test state.
- Preserve the existing Docker image, `linux/amd64` and `linux/arm64` image
  support, Raspberry Pi runtime, port, restart policy, timezone, and
  persistent-data volume behavior.
- Preserve the current production volume mapping. Repository examples contain
  differing host-directory names; verify the real deployment before changing
  a host path instead of choosing one by assumption.
- Do not change CI/CD, image publication, deployment, ports, domains, tunnels,
  authentication, or external exposure unless explicitly approved.

## Safety and Protected State

- Preserve unrelated user and other-agent changes. Treat unexpected diffs as
  having unknown authorship and keep them outside the current task unless
  confirmed.
- Do not inspect secrets, credentials, personal data, CFN cookies or sessions,
  CAPCOM IDs or passwords, local settings, `data/`, production databases, or
  production volumes unless their contents are strictly necessary for the
  approved task.
- Do not edit secrets, credentials, `.env`, local settings, production data,
  SQLite databases, runtime state, container state, volumes, or generated
  heavy artifacts unless the approved task explicitly requires the change.
- Never reproduce secrets, credentials, personal data, CFN session data,
  production records, or private infrastructure values in prompts, handoffs,
  fixtures, logs, API responses, reports, or external tools.
- Do not add dependencies or change build tooling, packaging, CI/CD,
  deployment, or external exposure outside the approved task scope.
- Do not commit, push, or publish images unless explicitly requested. A bounded reversible implementation/fix request includes deployment/application and any needed restart through the verified known procedure to the established user-controlled target; production data, volumes, credentials, external exposure, image publication, and new targets remain separately gated.

## Handoff Workflow

- Keep policy, design, review, investigation, and small documentation changes
  in Codex. Delegate only after the goal, files, constraints, non-goals, data
  sources, acceptance criteria, and verification are clear and material design
  choices are resolved.
- One handoff covers one cohesive, independently verifiable route, service
  behavior, or lifecycle path plus its direct regression coverage.
- Put substantive handoffs in
  `docs/handoffs/YYYY-MM-DD-<short-task>.md` with the data sources and
  acceptance criteria named. Run unresolved discovery as a separate read-only
  slice.
- Treat a delegation that ends before meeting its acceptance criteria as
  interrupted even when its process exits normally. Record usable partial
  results, verification, remaining scope, and the resume condition; narrow an
  over-broad handoff before rerunning it.
- The implementer returns design questions to Codex. Codex reviews the report
  and diff before preparing another slice.
- Keep active or blocked handoffs in `docs/handoffs/`. Move a handoff to
  `docs/handoffs/archive/` only after implementation, verification, review,
  required runtime work, and follow-up are complete.

## Review, Verification, and Documentation

Review scope, route contracts, scraping behavior, protected data, SQLite
compatibility, dependencies, deployment, external exposure, verification, and
unrelated diffs. The available automated suite is:

```powershell
python -m pytest
```

Use `git diff --check` for changed text. A runtime smoke check on port 8510
must use isolated data and credentials because starting `app.py` also starts
the scheduler; do not point an ad hoc check at production state.

Keep `AGENTS.md` short and current. Put decision context in `docs/decisions/`,
reusable technical notes under `docs/`, code-improvement candidates in
`docs/improvements.md`, feature ideas in `issues.md`, active or blocked
handoffs in `docs/handoffs/`, and completed handoffs in its `archive/`.

## Personal-Use Iteration

- Treat routine changes as personal-use iteration by default unless a verified project requirement or protected public-content, rights, human-approval, or data gate is stronger. Start with the smallest useful change and, when useful, a brief source or normal-path check; when it plausibly works, apply it through the verified known procedure to the established user-controlled target, including any needed restart, smoke normal use, and fix errors observed there.
- This allowance covers bounded reversible work only. Preserve gates for credentials, authentication, permissions, external exposure, live data, SQLite migrations, production volumes, infrastructure or cost, publication or release, and other project-specific protected behavior. Do not require speculative edge-case matrices, defensive hardening, or a full suite merely to permit ordinary iteration.
- If a target, check, or required approval is unavailable, distinguish source readiness from verified operation. Only important REQUIRED deferred checks belong in the existing issue or ledger, with their verification, approval, and resume conditions; optional or unnecessary checks do not create issues. Reconcile any operational checklist with the exact approval scope and conditions without weakening permanent prohibitions. For documentation-only changes, use the smallest relevant reference, fence, format, or sample check; do not invent an application runtime.
- If a project-required safety or approval review must precede application, return the stable source or diff with applicable pre-application checks first; runtime application and smoke are not run, passed, or complete until that gate clears. Ordinary work does not acquire review solely because optional checks were omitted.
