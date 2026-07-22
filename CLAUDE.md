# CLAUDE.md

## Purpose

This file defines Claude Code execution rules for `sf6-logs`. `AGENTS.md` owns
design intent, model selection, handoff policy, and Codex review.

## Project Context

- Entry point: `app.py`; it creates the Flask app, registers routes and filters,
  starts the scheduler, and serves on port 8510.
- Stack: Python, Flask, SQLite, APScheduler, requests, BeautifulSoup, Jinja2,
  vanilla JavaScript, and Docker.
- Main boundaries: `routes/` for HTTP behavior, `services/` for scraping,
  scheduling, statistics, and storage, and `templates/`/`static/` for dashboard
  and OBS presentation.
- GitHub Actions publishes `linux/amd64` and `linux/arm64` images. Production
  runs through Docker on a Raspberry Pi and persists `/app/data` through the
  existing host volume mapping.
- Repository examples disagree on the production host path. Neither example is
  authoritative without runtime confirmation.

## Instruction Handling

- Apply the instruction precedence defined in `AGENTS.md`.
- The active handoff or equivalent inline prompt is the approved task scope. It
  may narrow durable project constraints but may not weaken them.
- If instructions conflict or a required choice is unresolved, stop and return
  the conflict or design question to Codex instead of guessing.

## Execution Rules

- If the user writes in Japanese, respond in Japanese. Preserve the repository's
  established language for documentation, comments, identifiers, logs, and
  user-facing text unless the task changes it.
- Keep delegated Windows command lines ASCII-only. Put non-ASCII instructions
  in the UTF-8 handoff file instead of embedding them in the command line.
- Before editing, read `AGENTS.md`, this file, the supplied handoff or approved
  inline scope, and the files and current records listed for inspection.
- Before editing, capture `git status --short`. After editing, compare the final
  status and diff with that baseline. Do not reset, clean, stage, or rewrite
  pre-existing changes.
- Implement and report only the current independently verifiable slice. Wait
  for Codex review before starting a later slice.
- If listed files are insufficient for the first scoped edit, or a schema,
  dependency, deployment, volume, port, domain, authentication, or
  external-exposure change is required outside scope, stop and return the
  question to Codex.
- Preserve route contracts, CFN request pacing, scheduler behavior,
  authentication safeguards, SQLite compatibility, and mock/test isolation.
- Follow existing lightweight patterns and use minimal dependencies.
- Subagents are optional and limited to clearly parallel mechanical work within
  the same files, scope, and constraints.
- Preserve unrelated user and other-agent changes. Treat unexpected diffs as
  having unknown authorship and exclude them from the task unless confirmed.
- Do not commit, push, deploy, publish images, or operate production unless the
  approved task explicitly includes the action.

## Safety and Environment

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
- Preserve the Docker image, `linux/amd64` and `linux/arm64` support, runtime
  port, restart/timezone behavior, volume mapping, CI/CD, and exposure boundary.
- Do not choose between conflicting example host paths. Preserve the existing
  volume mapping, verify the real deployment, and return the question to Codex
  if an exact host path is required.
- Do not add dependencies or change build tooling, packaging, CI/CD,
  deployment, ports, domains, tunnels, authentication, or external exposure
  outside explicit scope.

## Verification and Report

Run the smallest relevant checks. The current automated suite is:

```powershell
python -m pytest
```

For documentation-only changes, use
`git diff --check -- AGENTS.md CLAUDE.md` and a focused reference scan. Start
`python app.py` for a manual port-8510 smoke check only with isolated data and
credentials and when runtime verification is explicitly appropriate; startup
initializes the database and starts the scheduler and its CFN-facing jobs.

Report changed files, a concise summary, verification commands and results,
blocked checks, pre-existing and partial edits left in the worktree, subagent
usage, unexpected findings, and design questions for Codex. If acceptance
criteria are unmet, report `status=interrupted`, usable partial results,
remaining scope, and the exact resume condition.
