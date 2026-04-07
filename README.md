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
- **Activity Calendar** -- GitHub 風ヒートマップ (過去 90 日)
- **時間帯別パフォーマンス** -- 0-23 時の勝率・試合数 (SVG 棒グラフ)
- **連勝/連敗 記録** -- Best Win Streak / Worst Lose Streak
- **再戦検知** -- 連続で同じ相手との対戦をグルーピング表示
- **期間フィルタ** -- All / 1 Day / 24h / 8h / 1h + 日付指定
- **バトルモードフィルタ** -- Ranked / Casual / Battle Hub / Custom
- **テーマ切替** -- Dark / Light / SF6

### OBS Overlay

| エンドポイント | 内容 |
|---|---|
| `/overlay` | Full (W/L + LP/MR + Match History) |
| `/overlay/record` | W/L + WinRate のみ |
| `/overlay/lp` | LP/MR のみ |
| `/overlay/history` | 直近の勝敗ドットのみ |
| `/overlay/popup` | ポップアップ通知 (イベント発生時のみ表示) |

**オプション (クエリパラメータ)**

| パラメータ | 値 | デフォルト |
|---|---|---|
| `theme` | `dark` / `sf6` | `dark` |
| `size` | `small` / `medium` / `large` | `medium` |
| `layout` | `vertical` / `horizontal` | `vertical` |
| `mode` | `all` / `ranked` / `casual` / `battle_hub` / `custom` | `all` |
| `anim` | `1` / `0` | `1` |
| `streak` | `1` / `0` | `1` |
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

1. http://localhost:8510/settings にアクセス
2. **CFN User ID** に Buckler's Boot Camp のプロフィール URL の数字 ID を入力
3. **CFN Cookie** を設定 (ブラウザ DevTools からコピー) または **CAPCOM ID** で自動ログイン設定
4. Mock Mode を OFF にすると実データの取得を開始 (ポーリング間隔: 90 秒)

## Directory Structure

```
sf6-logs/
  app.py              # Flask エントリーポイント
  config.py           # 設定値・定数
  routes/             # Flask Blueprint (画面ごとに分割)
    api.py            #   REST API + SSE
    dashboard.py      #   ダッシュボード
    overlay.py        #   OBS オーバーレイ
    settings.py       #   設定画面
  services/           # ビジネスロジック
    storage.py        #   DB 操作
    stats.py          #   統計計算
    cfn_scraper.py    #   CFN スクレイパー
    cfn_auth.py       #   CFN 認証
    scheduler.py      #   APScheduler
  templates/          # Jinja2 テンプレート
    overlay/          #   OBS オーバーレイ用
  static/             # CSS/JS
  data/               # SQLite DB (gitignore)
```

## License

Private repository.
