# 2026-07-08: improvements checklist implementation

## Context
`docs/improvements.md` listed stability, bug, performance, and maintainability items from the 2026-07-07 codebase review. The user requested Codex-only implementation and asked to include all current diffs in the commit.

## Decisions
- Keep `services.stats` as the public compatibility facade for route imports.
- Split stats implementation by responsibility into aggregate helpers, record/notification helpers, and report/goal helpers.
- Keep streak record writes on match insertion only. Read APIs may compare computed values with saved records, but must not update `streak_records`.
- Limit SSE clients in-process and return HTTP 503 when the limit is exceeded. Existing overlay polling fallback remains the recovery path.
- Exclude `raw_data` from normal match query helpers used by dashboard and stats aggregation.

## Verification
- `python -m py_compile app.py config.py routes\api.py routes\settings.py routes\filters.py services\storage.py services\stats.py services\stats_aggregates.py services\stats_records.py services\stats_reports.py services\cfn_auth.py services\cfn_scraper.py services\scheduler.py tests\test_core.py`
- `python -m pytest`
- `git diff --check`
