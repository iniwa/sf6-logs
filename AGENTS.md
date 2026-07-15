# AGENTS.md

## Purpose

This is the Codex-side working agreement for `sf6-logs`. It records durable
product and data constraints, model and handoff policy, review rules, and
documentation lifecycle. `CLAUDE.md` contains Claude Code execution rules.

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

## Model and Role Policy

- Use GPT-5.3-Codex-Spark (`gpt-5.3-codex-spark`) proactively, when available,
  for low-risk, well-scoped, independently verifiable supporting work that
  requires no material design judgment or source-code implementation.
- GPT-5.6 Terra (`gpt-5.6-terra`) or Sol (`gpt-5.6-sol`) owns requirements and
  design. Whenever Terra is used, set its reasoning level to `high`. Prefer Sol
  for substantial ambiguity, risk, or cross-boundary reasoning.
- After design is fixed, delegate source-code implementation first to Claude
  Code Sonnet 5 at effort medium from the repository root.
- Only when Sonnet 5 is unavailable because of usage limits or service
  availability, use GPT-5.6 Luna (`gpt-5.6-luna`) with reasoning level `max`
  for the same implementation slice.
- Implementation failure, failed verification, or a design question is not
  model unavailability; return it to Codex.
- Apply this policy to every coordinating Codex model and its subagents. Do not
  create coordinator-specific exceptions.
- Codex may keep requirements, design, review, read-only investigation,
  synthesis, and small documentation-consistency changes in one context.

## Durable Project Rules

- Preserve the existing dashboard, report, settings, API, SSE, and OBS overlay
  routes and their documented URL contracts.
- Treat CFN/Buckler behavior as an external integration. Preserve request
  pacing, authentication handling, parsing safeguards, and mock/test isolation;
  do not increase live request frequency casually.
- Preserve SQLite compatibility unless an explicit migration is designed and
  verified. Production match data, sessions, settings, and stored credentials
  are user data, not disposable test state.
- Never expose or log CFN cookies, CAPCOM IDs, passwords, or configuration
  records containing credentials.
- Preserve the existing Docker image, multi-architecture support, runtime port,
  restart policy, timezone, and persistent-data volume behavior.
- Preserve the current production volume mapping. Repository examples contain
  differing host-directory names; verify the real deployment before changing
  a host path instead of choosing one by assumption.
- Do not change CI/CD, image publication, deployment, ports, domains, tunnels,
  authentication, or external exposure unless explicitly approved.
- Do not commit, push, or deploy unless explicitly requested.

## Protected Files and State

- Do not read, edit, delete, print, or commit `.env`, local settings, `data/`,
  SQLite production databases, cookies, CAPCOM credentials, container runtime
  state, or production volumes unless an approved task explicitly requires it.
- Preserve unrelated working-tree changes. Treat unexpected diffs as having
  unknown authorship and exclude them from the current task.

## Handoff Workflow

- Keep policy, design, review, investigation, and small documentation changes
  in Codex. Delegate only after the goal, files, constraints, non-goals, data
  sources, and verification are clear.
- One handoff covers one cohesive, independently verifiable route, service
  behavior, or lifecycle path plus its direct regression coverage.
- Put substantive handoffs in
  `docs/handoffs/YYYY-MM-DD-<short-task>.md`. Run unresolved discovery as a
  separate read-only slice.
- If a broad handoff times out before its intended edit, do not rerun it
  unchanged. Narrow the behavior, files, and verification first.
- The implementer changes only the current slice and returns design questions
  to Codex. Codex reviews the report and diff before preparing another slice.
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
