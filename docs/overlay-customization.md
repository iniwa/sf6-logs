# OBS オーバーレイ カスタマイズメモ

## 現状（Phase 1）

`/overlay` に全部入りオーバーレイのみ実装。

- 表示内容: 今日の勝敗 (W/L)、勝率、LP、MR、直近10戦の勝敗ドット
- 更新: JS `setInterval` で 5秒ごとに `/api/stats/today` と `/api/matches?limit=10` をポーリング
- 背景: `transparent`（OBS ブラウザソース向け）
- 外部 CDN: 不使用（LAN 内完結）

## Phase 2 で追加予定

### 分割オーバーレイ URL

| URL | 表示内容 |
|-----|----------|
| `/overlay` | 全部入り（現在実装済み） |
| `/overlay/record` | 勝敗のみ |
| `/overlay/lp` | LP/MR 変動のみ |
| `/overlay/history` | 直近履歴のみ |

### カスタマイズパラメータ

- `?theme=dark|sf6` — テーマ切替
- `?size=small|medium|large` — フォントサイズ
- `?scope=session|today` — 集計範囲（セッション or 本日）

### 更新方式の改善

Phase 1 は `setInterval` + `fetch` でポーリング。
Phase 2 で SSE (Server-Sent Events) への切替を検討。

## 調整が多い箇所

- `templates/overlay/full.html` — レイアウト・スタイル調整
- `static/css/common.css` — テーマカラー
- `routes/overlay.py` — 分割オーバーレイ追加時にルート追加
- `services/stats.py` — スコープ切替に伴う統計クエリ変更
