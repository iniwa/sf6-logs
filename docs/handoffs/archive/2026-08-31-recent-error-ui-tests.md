# Recent-error JavaScript behavior checks

Status: complete; final Node behavior and syntax checks passed.

## Boundary

This is a fresh, narrow test-only slice after the parent implementation
contract reset. The primary owns all production files and Python tests.
One `bounded_implementer` owns only new `tests/test_recent_errors_ui.js`.
Preserve other work; no package/dependency changes, browser automation, live
network, app startup, commits, or deployment.

## Sources and outcome

Read `AGENTS.md`, `static/js/common.js`, `templates/dashboard.html`, and the
settled UI requirements in `2026-08-31-recent-error-history.md` in this folder.
Write a standalone Node test using only `node:assert/strict`, `node:vm`, and
`node:fs` (path helpers as needed). Load `common.js` into a VM with tiny
document/element/fetch/timer/localStorage fakes; do not add a DOM library.

Verify populated/empty rendering, row order and fields, absence of an HTTP
code, and literal text handling of synthetic HTML-shaped event fields. Make
an `innerHTML` write fail so the test enforces text-only rendering. Check
seconds and explicit JST in time display. Verify pages without the history
container still update badges. Exercise DOMContentLoaded and the existing
timer callback: exactly one ten-second timer, only `/api/status` requests,
and no additional timer/request caused by history rendering. An old/missing
history field should not throw or erase already-rendered data.

Run `node tests/test_recent_errors_ui.js`. If assertions find a product bug,
report the exact failing expectation to the primary; do not edit production
files or weaken the expectation. Self-review and stop editing before return.

## Verification

The test identified a missing JST label in the live formatter; the primary
fixed it. The test helper was corrected to drain the asynchronous Promise
chain with one `setImmediate` turn (no timed sleep). The complete standalone
Node test and syntax check now pass. Source behavior is verified; no browser
was available for visual inspection.
