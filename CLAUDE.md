# CLAUDE.md


## Codex / Claude Code Workflow
- This `CLAUDE.md` is for Claude Code execution rules.
- Codex handoffs should normally be saved under `docs/handoffs/`; when a handoff file path is provided, read it before editing.
- If the project also has `AGENTS.md`, treat it as the Codex-side source of design intent, handoff rules, and review criteria.
- When the user provides a Codex handoff, follow that handoff first, then this file, then local project conventions.
- If the task is ambiguous, requires changing documented design intent, or needs files outside the handoff, stop and ask before editing.
- Do not commit automatically unless explicitly requested.
- Report changed files, summary, verification results, blocked checks, and any design questions that should return to Codex.

## Model / Subagent Policy
- Run in auto mode (automatic model selection) by default. No fixed coordinator model.
- Codex owns design decisions; handoffs (`docs/handoffs/`) are written so implementation completes without design judgment.
- Subagents are optional — use them only when isolation helps (broad scans, parallel mechanical edits), with a narrow goal, explicit file scope, constraints, and non-goals.
- Do not change documented design intent, add dependencies, or alter build/deploy/external exposure without returning the question to Codex.
- If the intended mode or model is unavailable, continue with the available one and report that limitation.

## Project Overview
SF6 Stats Tracker — Street Fighter 6 の対戦成績（LP/MR、勝敗、キャラ別戦績）を自動取得し、ダッシュボードと OBS オーバーレイで表示する Web ツール。Buckler's Boot Camp (CFN) から _next/data API 経由でスクレイピングし、SQLite に蓄積する。

## Tech Stack
- Python / Flask
- SQLite (`data/stats.db`)
- APScheduler (ポーリング)
- BeautifulSoup / requests (CFN スクレイピング)
- Jinja2 テンプレート + vanilla JS

## Structure
```
app.py                  # エントリポイント (Flask, port 8510)
config.py               # 共有設定・ログ・JST 定義
routes/                 # Blueprint: dashboard, report, overlay, settings, api + filters (Jinja フィルタ)
services/               # cfn_auth, cfn_scraper, scheduler, stats, storage
templates/              # Jinja2 テンプレート (overlay/ 配下に OBS 用)
static/                 # CSS / JS
docs/                   # 設計メモ・decisions/ (設計履歴)・handoffs/ (Codex handoff)・improvements.md (改善チェックリスト)
issues.md               # 機能追加アイデアの管理
```

## Verification
- 自動テスト / lint は未整備（導入候補は `docs/improvements.md` 参照）。
- 最低限の確認: `git diff --check`、`python app.py` が起動して :8510 が応答すること。
- 保護対象: `data/`（SQLite 実データ）、認証情報（cookie / CAPCOM ID は DB の config テーブルに保存される）。

## Coding Style
- Write lightweight, efficient code. Prefer minimal dependencies.

## Environment
- Host: Raspberry Pi 4 (8GB RAM), `linux/arm64`
- Docker management: Portainer — Stack Web Editor only (no direct compose files)

### Work Location Detection
- Working in `D:/Git/` → **Home (Sub PC)**
- Working in `C:/Git/` → **Home (Main PC)**
- Working in `C:/Users/**/Documents/git/` → **Remote PC**
  - Remote PC lacks required environments. Focus on code adjustments only.
- Can SSH into Raspberry Pi via `ssh iniwapi` to read code/logs from the Pi

## Build & Deploy
- Build target: `linux/arm64`
- Image: `ghcr.io/iniwa/sf6-logs:latest`
- Flow: push to `main` → GitHub Actions → GHCR → Portainer Stack paste
- All containers require: `restart: unless-stopped`, `TZ=Asia/Tokyo`
- Resource limits: consider `deploy.resources.limits.memory` — host is 8GB shared across all containers

## Storage
| Data | Path | Backend |
|------|------|---------|
| Container data / DB | `/home/iniwa/docker/sf6-stats/data` | SSD (primary) |
| Git repo / LFS | `/mnt/nas/git-data/` | NFS |

## External Access
Cloudflared (Cloudflare Tunnel) is installed. Configure tunnel when exposing a service externally.

## Knowledge Persistence
- Actively save design decisions, architecture notes, and reusable patterns to `docs/*.md`
- Before starting work, check `docs/` for existing context that may be relevant
- Detailed design history belongs in `docs/decisions/`. Keep `AGENTS.md` focused on short, durable rules; do not add `Alternatives Considered` as a default Decision Log heading there.

## Tooling
- Use **Serena MCP** tools for code navigation and editing to maximize efficiency (symbol search, overview, replace, insert, etc.)
- Use **Tavily MCP** for web research. When you need external information (library docs, API references, error solutions, best practices), proactively use Tavily search/research instead of relying solely on training data.

## New Tool Checklist
- [ ] arm64-compatible base image (`alpine` preferred)
- [ ] `TZ=Asia/Tokyo` in environment
- [ ] `restart: unless-stopped`
- [ ] Image: `ghcr.io/iniwa/{tool-name}:latest`
- [ ] GitHub Actions workflow at `.github/workflows/docker-publish.yml`
- [ ] `.claudeignore` in project root
- [ ] Verify deployment via Portainer Stack
- [ ] Configure Cloudflare Tunnel if external access is needed
