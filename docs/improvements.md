# プログラム改善チェックリスト

コードベースを調査して洗い出した改善候補の一覧（2026-07-07 調査）。

**運用方法**: 着手したい項目にチェック `[x]` を入れる → Codex が handoff
（`docs/handoffs/`）を作成し、Claude Code（auto モード）が実装する。
handoff を挟むまでもない小粒な項目は Claude Code に直接依頼してもよい。
実装完了した項目は「完了アーカイブ」へ移動する。

- 機能追加・未検証項目はこのファイルの対象外（`issues.md` で管理）。
- 優先度: **高** = 稼働中の安定性・動作に直結 / **中** = 保守性・性能 / **低** = 任意。

---

## 1. 安定性

（現在なし）

## 2. 実バグ

（現在なし）

## 3. 構造・保守性

（現在なし）

---

## 完了アーカイブ

### 2026-07-08

- [x] **【高】SSE `/api/stream` による waitress スレッド枯渇を防ぐ**
  - waitress `threads` を 32 に引き上げ、SSE 同時接続上限を 16 に制限。上限超過時は 503 を返し、通常オーバーレイは既存の polling fallback に移行する。
- [x] **【中】post-insert hook の例外を無ログで握りつぶさない**
  - hook 例外を `c.log(..., exc_info=True)` で記録するように変更。
- [x] **【低】例外ログにスタックトレースを残せるようにする**
  - `config.log()` を標準 `logging` ベースにし、主要な例外ログで `exc_info=True` を使用。
- [x] **【高】`popup_lp_mr_delta` 設定が機能していないのを直す**
  - match SSE payload に `show_lp_mr_delta` を含め、popup 側で LP/MR 差分表示を抑制。
- [x] **【中】stats 用の全件クエリから `raw_data` を除外する**
  - `matches` 取得の共通 SELECT を明示カラム化し、集計・画面表示で replay JSON 全体を読まないように変更。
- [x] **【中】streak 記録の更新経路を一本化する**
  - `get_best_streaks()` は読み取り専用にし、DB 記録更新は挿入時の `check_streak_record()` に一本化。
- [x] **【中】`services/stats.py`（1035 行）を責務で分割する**
  - `stats_aggregates.py`、`stats_records.py`、`stats_reports.py` に分割し、`services.stats` は既存 import 互換の facade として維持。
- [x] **【中】pytest 基盤と中核ロジックのユニットテストを追加する**
  - `tests/test_core.py` を追加し、CFN parse、streak 計算、LP/MR migration、scheduler backfill を検証。
- [x] **【低】`routes/filters.py:3` の未使用 `JST` 定義を削除する**
  - 未使用 import と重複定義を削除。
- [x] **【低】`/api/sessions` の N+1 クエリを解消する**
  - session summary を 1 本の集計 SQL で返す `storage.get_session_summaries()` に変更。
- [x] **【低】`routes/api.py:93` の `stats._UNSET` 私有センチネル依存を解消する**
  - `stats.UNSET` を公開名として追加し、API 側は公開名を参照。
