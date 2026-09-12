# SF6 Stats Tracker

Street Fighter 6 の対戦データを [CFN (Buckler's Boot Camp)](https://www.streetfighter.com/6/buckler/) から自動取得し、統計ダッシュボードと OBS オーバーレイを提供する Web アプリケーション。

## Features

### Dashboard (`/`)

- **戦績サマリー** -- W/L/勝率、LP/MR、セッション差分を表示
- **Match History** -- 直近の対戦履歴 (対戦相手キャラ・MR/LP・結果)
- **キャラ別勝率** / **対戦相手別勝率** / **マッチアップ別勝率**
- **LP/MR 推移グラフ** -- 折れ線グラフで LP/MR の変動を可視化
- **ローリング勝率** -- 直近 10 戦 / 20 戦の勝率推移 (SVG 折れ線グラフ)
- **キャラ別マッチアップヒートマップ** -- 自キャラ x 相手キャラの勝率を色分け表示
- **Activity Calendar** -- GitHub 風ヒートマップ (直近 90 日 / 年単位表示の切替可)
- **時間帯別パフォーマンス** -- 0-23 時の勝率・試合数 (SVG 棒グラフ)
- **曜日 x 時間帯ヒートマップ** -- 曜日 x 時間帯ごとの勝率を色分け表示
- **セッション疲労** -- 連戦時の試合数経過による勝率推移
- **連勝/連敗 記録** -- Best Win Streak / Worst Lose Streak
- **再戦検知** -- 同じ相手との連戦 (4 戦以上) をグルーピング表示
- **期間フィルタ** -- 直近 20 / 100 / 200 戦 / All / カスタム N 戦 + 日付指定
- **バトルモードフィルタ** -- Ranked / Casual / Battle Hub / Custom
- **キャラフィルタ** -- 使用キャラで絞り込み
- **テーマ切替** -- Dark / Light / SF6

### Report (`/report`)

- **週間 / 月間レポート** -- 過去 7 日 / 30 日の日別集計・勝率
- **Personal Records** -- 歴代の自己記録一覧
- バトルモードフィルタ対応

### OBS Overlay

| エンドポイント | 内容 |
|---|---|
| `/overlay` | Full (W/L + LP/MR + Match History) |
| `/overlay/record` | W/L + WinRate のみ |
| `/overlay/lp` | LP/MR のみ |
| `/overlay/history` | 直近の勝敗ドットのみ |
| `/overlay/popup` | ポップアップ通知 (イベント発生時のみ表示) |
| `/overlay/highlight` | セッションサマリー (W/L・勝率・LP/MR 変動・ベスト連勝) |
| `/overlay/preview` | Overlay Settings 用のプレビュー画面 |

**オプション (クエリパラメータ)**

| パラメータ | 値 | デフォルト |
|---|---|---|
| `theme` | `dark` / `sf6` | `dark` |
| `size` | `small` / `medium` / `large` | `medium` |
| `layout` | `vertical` / `horizontal` | `vertical` |
| `mode` | `all` / `ranked` / `casual` / `battle_hub` / `custom` | `all` |
| `anim` | `1` / `0` | `1` |
| `streak` | `1` / `0` | `1` |
| `pos` | `right` / `left` | `right` |
| `char` | `auto` (直近使用キャラ) / キャラ名 | -- (フィルタなし) |
| `goal` | `1` (目標プログレスバー表示) / `0` | `0` |
| `test` | `1` (Popup のみ: 常時表示テストモード) | -- |

### Popup Notification

SSE (Server-Sent Events) でリアルタイム通知。各通知は Overlay Settings で ON/OFF 可能。

| 通知タイプ | 内容 |
|---|---|
| Match Result | WIN/LOSE 表示 |
| LP/MR Delta | LP/MR の増減値 |
| Rank Change | ランク昇格/降格 |
| MR Milestone | MR 100 刻みの到達通知 (例: "1500 MASTER 到達!") |
| Streak Record | 連勝/連敗の最高記録更新 |
| Best MR | 最高 MR 更新時 |

### Settings

- **CFN Settings** (`/settings`) -- Buckler's Boot Camp の認証情報設定、Mock Mode 切替
- **直近のエラー履歴** -- Settings 下部に直近20件を表示。取得成功後も残り、10秒ごとに表示を更新（アプリ再起動で消去）
- **Overlay Settings** (`/overlay-settings`) -- Overlay URL Builder、ポップアップ通知設定、セッション管理、OBS 推奨解像度

### Session Management

配信セッション単位で成績をリセット。Overlay Settings から開始/終了を操作、セッション履歴で過去のセッション成績を確認可能。

## OBS Browser Source Setup

### 推奨解像度

| Type | Width | Height |
|---|---|---|
| Full (Vertical) | 500 | 180 |
| Full (Horizontal) | 700 | 100 |
| Record Only | 300 | 80 |
| LP / MR Only | 250 | 60 |
| Match History | 500 | 60 |
| Popup Notification | 400 | 200 |

> Size を Large にする場合は各値を 1.3-1.5 倍に調整してください。

### 設定手順

1. OBS で **ソース > ブラウザ** を追加
2. URL に `http://<host>:8510/overlay` (常時表示) を設定
3. 幅・高さを上記の推奨値に設定
4. **ポップアップ通知用に別のブラウザソースを追加**: URL に `http://<host>:8510/overlay/popup` を設定
5. Popup ソースは画面上の目立つ位置に配置 (通知がないときは透明)

> 配置確認には `/overlay/popup?test=1` を使うとポップアップが常時表示されます。

## Tech Stack

- **Python 3.11+** / **Flask**
- **SQLite** (データ永続化)
- **APScheduler** (CFN ポーリング)
- **requests** + **BeautifulSoup** (スクレイピング)
- **Jinja2** + HTML/CSS/JS (テンプレート、外部 CDN 不使用)
- **SSE** (Server-Sent Events) でリアルタイム更新
- **Docker** (`linux/amd64` + `linux/arm64`)

## Setup

### ローカル実行

```bash
pip install -r requirements.txt
python app.py
```

http://localhost:8510 でアクセス。

### Docker

```bash
docker build -t sf6-stats .
docker run -d \
  -p 8510:8510 \
  -v sf6-data:/app/data \
  -e TZ=Asia/Tokyo \
  --restart unless-stopped \
  sf6-stats
```

### Portainer Stack

```yaml
services:
  sf6-logs:
    image: ghcr.io/iniwa/sf6-logs:latest
    ports:
      - "8510:8510"
    volumes:
      - /home/iniwa/docker/sf6-logs:/app/data
    environment:
      - TZ=Asia/Tokyo
    restart: unless-stopped
```

### CI/CD

`main` ブランチへの push で GitHub Actions が `linux/amd64` + `linux/arm64` のマルチアーキテクチャイメージをビルドし、GHCR (`ghcr.io/iniwa/sf6-logs:latest`) にプッシュします。

## Initial Configuration

### 認証エラーからの復旧（Docker / Portainer）

DockerイメージにはPlaywrightとChromiumを同梱します。requestsでのログインが
失敗した場合にブラウザログインを試みます。対応するDebianベースのイメージを使い、
`linux/amd64` / `linux/arm64` の両方で同じDockerfileを使用します。
ブラウザ追加によりイメージサイズとログイン時のメモリ使用量は増えます。

`Auth page ... 403` はパスワード送信前に認証ページが拒否された状態です。
ブラウザでもアクセス制限や追加認証が出る場合は、Settingsの「403・自動ログイン
失敗時の復旧手順」に従って、PCでログイン後のCookieを手動更新してください。
Cookie更新後は認証エラーの待機を短縮し、通常90秒程度で取得を再試行します。
取得成功までは現在のエラーを維持し、成功後も履歴は保持します。
通信エラーや429による待機はCookie更新では解除しません。

既存のPortainerコンテナにはソース変更だけでは反映されません。
変更を含むイメージをビルド・公開した後、Portainerでそのイメージを取得して
再デプロイします。既存のポート、再起動ポリシー、`TZ`、`/app/data` の
永続ボリューム設定を維持してください。コンテナ内への一時的なpip installは不要です。
反映後はSettingsの「Test Auto-Login」で結果を確認し、次の取得成功を確認します。
Playwrightの同梱だけでCAPCOM側の403解消が保証されるわけではありません。

参考: [Playwright対応環境](https://playwright.dev/python/docs/intro)、
[ブラウザとシステム依存関係のインストール](https://playwright.dev/python/docs/browsers)。

### 設定手順

1. http://localhost:8510/settings にアクセス
2. **CFN User ID** に Buckler's Boot Camp のプロフィール URL の数字 ID を入力
3. **CFN Cookie** を設定 (ブラウザ DevTools からコピー) または **CAPCOM ID** で自動ログイン設定
4. Mock Mode を OFF にすると実データの取得を開始 (ポーリング間隔: デフォルト 90 秒、Settings で 5〜90 秒に変更可)

## Directory Structure

```
sf6-logs/
  app.py              # Flask エントリーポイント
  config.py           # 設定値・定数
  routes/             # Flask Blueprint (画面ごとに分割)
    api.py            #   REST API + SSE
    dashboard.py      #   ダッシュボード
    report.py         #   週間/月間レポート
    overlay.py        #   OBS オーバーレイ
    settings.py       #   設定画面
    filters.py        #   Jinja2 テンプレートフィルタ
  services/           # ビジネスロジック
    storage.py        #   DB 操作
    stats.py          #   統計計算
    cfn_scraper.py    #   CFN スクレイパー
    cfn_auth.py       #   CFN 認証
    scheduler.py      #   APScheduler
  templates/          # Jinja2 テンプレート
    overlay/          #   OBS オーバーレイ用
  static/             # CSS/JS
  docs/               # 設計メモ・decisions/・handoffs/・improvements.md
  issues.md           # 機能追加アイデアの管理
  data/               # SQLite DB (gitignore)
```

## Development Workflow

- **設計 → 実装の分担**: runtimeで選択されたprimaryが設計判断と handoff (`docs/handoffs/YYYY-MM-DD-*.md`) を担当し、実装・検証は `AGENTS.md` のnative Codex role policyと互換境界に従う。詳細は `AGENTS.md` / `CLAUDE.md` を参照。
- **改善候補**: コード品質・安定性の改善項目は `docs/improvements.md` のチェックリストで管理する。
- **機能追加アイデア**: `issues.md` で管理する。
- **検証**: `python -m pytest` と `git diff --check`。`app.py` の起動時にはスケジューラも開始するため、起動確認は本番とは別のデータ・認証設定で行う。

## License

[MIT License](LICENSE)
