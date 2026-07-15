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

## Execution Rules

- If the user writes in Japanese, respond in Japanese.
- Keep delegated Windows command lines ASCII-only. Put non-ASCII instructions
  in the UTF-8 handoff file instead of embedding them in the command line.
- Before editing, read `AGENTS.md`, this file, the supplied handoff, and the
  files and current records listed for inspection.
- Implement and report only the current independently verifiable slice. Stay
  within its approved files, constraints, and non-goals.
- If instructions conflict, listed files are insufficient for the first scoped
  edit, or a design, schema, dependency, deployment, volume, port, domain,
  authentication, or external-exposure change is required, stop and return the
  question to Codex.
- Preserve route contracts, CFN request pacing, authentication safeguards,
  SQLite compatibility, and existing mock/test isolation.
- Follow existing lightweight patterns and use minimal dependencies.
- Preserve unrelated changes and treat unexpected diffs as having unknown
  authorship.
- Do not commit, push, deploy, publish images, or operate production unless the
  approved task explicitly includes the action.

## Safety and Environment

- Do not read, edit, delete, print, or commit `.env`, local settings, `data/`,
  production SQLite databases, cookies, CAPCOM IDs, passwords, runtime state,
  or production volumes.
- Never include stored credentials in logs, API responses, fixtures, or reports.
- Preserve the current Docker image, supported architectures, runtime port,
  restart/timezone behavior, volume mapping, CI/CD, and exposure boundary.
- Do not choose between conflicting example host paths. Verify the real
  deployment and return the question to Codex if an exact path is required.
- Do not add dependencies or change build tooling, packaging, CI/CD,
  deployment, ports, domains, tunnels, authentication, or external exposure
  outside explicit scope.

## Verification and Report

Run the smallest relevant checks. The current automated suite is:

```powershell
python -m pytest
```

Also use `git diff --check` for changed text. Start `python app.py` for a manual
port-8510 smoke check only with isolated data and credentials and when runtime
verification is explicitly appropriate; startup also starts the scheduler.

Report changed files, a concise summary, verification commands and results,
blocked checks, subagent usage, unexpected findings, and design questions for
Codex.
