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

## Model and Role Policy

- Use GPT-5.3-Codex-Spark (`gpt-5.3-codex-spark`) proactively, when available,
  for low-risk, well-scoped, independently verifiable supporting work that
  requires no material design judgment or source-code implementation.
- GPT-5.6 Terra (`gpt-5.6-terra`) or Sol (`gpt-5.6-sol`) owns requirements and
  design. Whenever Terra is used, set its reasoning level to `high`. Prefer Sol
  for substantial ambiguity, risk, or cross-boundary reasoning.
- Run every Claude Code task with `--permission-mode auto`.
- After design is fixed, delegate source-code implementation first to Claude
  Code Sonnet at effort medium from the repository root:
  `claude -p --model sonnet --effort medium --permission-mode auto "<handoff/task prompt>"`.
- Only when Sonnet is unavailable because of usage limits or service
  availability, use GPT-5.6 Luna (`gpt-5.6-luna`) with reasoning level `max`
  for the same implementation slice.
- Implementation failure, failed verification, or a design question is not
  model unavailability; return it to Codex instead of switching models.
- Apply this policy to every coordinating Codex model and its subagents. Do not
  create coordinator-specific exceptions unless the user explicitly changes
  the policy.
- Claude Code subagents are optional and limited to clearly parallel mechanical
  work inside the current task scope. They inherit its constraints.
- Codex may keep requirements, design, review, read-only investigation,
  synthesis, and small documentation-consistency changes in one context.

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
- Do not commit, push, publish images, or deploy unless explicitly requested.

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
- Sonnet implements only the approved slice. Luna at reasoning level `max` may
  implement the same slice only under the model-unavailability condition above.
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
