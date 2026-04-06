# SF6 Stats Tracker — Issues / Remaining Tasks

## Phase 2: オーバーレイ改善

- [x] 分割オーバーレイURL (`/overlay/record`, `/overlay/lp`, `/overlay/history`)
- [x] テーマ切替 (`?theme=dark|sf6`)
- [x] サイズ切替パラメータ (`?size=small|medium|large`)
- [x] SSE (Server-Sent Events) によるリアルタイム更新（ポーリングフォールバック付き）

## Phase 2: ダッシュボード改善

- [x] キャラ別勝率の集計・表示
- [x] 対戦相手別統計
- [x] LP/MR 推移グラフ（インライン SVG）

## 自動ログイン関連

- [ ] 自動ログイン機能の実機テスト（ラズパイ Docker 環境）
- [ ] Cookie 有効期限の実測（どの程度で失効するか確認）
- [ ] 2FA 有効ユーザーへの対応（現在は 2FA 無効のみ対応）
- [ ] Auth0 側の仕様変更・CAPTCHA 追加時の対策（Playwright fallback 検討）

## インフラ / 運用

- [ ] Playwright fallback（ARM64 対応確認済み、必要時に導入）
- [ ] エラー時の exponential backoff 実装
- [ ] Cloudflare Tunnel による外部公開設定（必要に応じて）
