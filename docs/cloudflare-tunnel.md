# Cloudflare Tunnel 外部公開設定

## 概要

Cloudflare Tunnel を使って Raspberry Pi 上の SF6 Stats Tracker（port 8510）をインターネットに公開する手順。
ポート開放やリバースプロキシ不要で、Cloudflare のエッジ経由で安全に接続できる。

## 前提

- Raspberry Pi に `cloudflared` がインストール済み
- Cloudflare アカウントにドメインが追加済み
- SF6 Stats Tracker が `http://localhost:8510` で稼働中

## 1. Tunnel 作成

```bash
cloudflared tunnel login
cloudflared tunnel create sf6-stats
```

認証情報ファイルが `~/.cloudflared/` に生成される:

```
~/.cloudflared/cert.pem          # アカウント認証（login 時）
~/.cloudflared/<TUNNEL_ID>.json  # トンネル認証（create 時）
```

## 2. 設定ファイル

`~/.cloudflared/config.yml` を作成:

```yaml
tunnel: sf6-stats
credentials-file: /home/iniwa/.cloudflared/<TUNNEL_ID>.json

ingress:
  - hostname: sf6.example.com
    service: http://localhost:8510
  - service: http_status:404
```

`hostname` は実際のサブドメインに置き換える。

## 3. DNS ルーティング

```bash
cloudflared tunnel route dns sf6-stats sf6.example.com
```

Cloudflare DNS に CNAME レコード（`<TUNNEL_ID>.cfargotunnel.com`）が自動作成される。

## 4. 動作確認

```bash
cloudflared tunnel run sf6-stats
```

`https://sf6.example.com` でダッシュボードにアクセスできることを確認。

## 5. systemd サービス化

```bash
sudo cloudflared service install
sudo systemctl enable cloudflared
sudo systemctl start cloudflared
```

設定ファイルが `/etc/cloudflared/config.yml` にコピーされる。
既に `~/.cloudflared/config.yml` に書いた内容をそちらにも反映すること。

## 6. Docker コンテナで運用する場合（Portainer Stack）

cloudflared を sf6-stats と同じ Stack 内でコンテナとして動かす方法。
Portainer の Stack Web Editor に以下を追加する。

```yaml
services:
  sf6-stats:
    image: ghcr.io/iniwa/sf6-logs:latest
    container_name: sf6-stats
    restart: unless-stopped
    ports:
      - "8510:8510"
    volumes:
      - /home/iniwa/docker/sf6-stats/data:/app/data
    environment:
      - TZ=Asia/Tokyo

  cloudflared:
    image: cloudflare/cloudflared:latest
    container_name: sf6-cloudflared
    restart: unless-stopped
    command: tunnel --no-autoupdate run --token ${CLOUDFLARED_TOKEN}
    environment:
      - TZ=Asia/Tokyo
    deploy:
      resources:
        limits:
          memory: 128M
```

### Token の取得

Cloudflare Zero Trust ダッシュボード → Networks → Tunnels → トンネル作成時に表示される Token を使う。
Portainer の Stack 環境変数に `CLOUDFLARED_TOKEN` を設定する。

> **注意**: Docker コンテナ方式の場合、`service` の URL は `http://sf6-stats:8510`（コンテナ名で解決）になる。
> Cloudflare Zero Trust ダッシュボードの Public Hostname 設定で指定する。

## 7. セキュリティに関する注意

### Settings ページの保護

Settings ページ（`/settings`）では CAPCOM ID のメールアドレス・パスワードや Cookie を扱う。
外部公開する場合、**必ずアクセス制限を設ける**こと。

#### 方法 A: Cloudflare Access で認証を追加

Cloudflare Zero Trust → Access → Applications でアプリケーションを追加:

- Application domain: `sf6.example.com`
- Policy: メールアドレスのワンタイムパスワード認証など

これにより全ページにログインが必要になる。

#### 方法 B: オーバーレイのみ公開

`config.yml` の ingress でパスを制限し、オーバーレイ関連のみ公開する:

```yaml
ingress:
  - hostname: sf6.example.com
    path: /overlay.*
    service: http://localhost:8510
  - hostname: sf6.example.com
    path: /api/stats/.*
    service: http://localhost:8510
  - hostname: sf6.example.com
    path: /api/matches.*
    service: http://localhost:8510
  - hostname: sf6.example.com
    path: /static/.*
    service: http://localhost:8510
  - service: http_status:403
```

ダッシュボードや Settings ページへの外部アクセスを遮断できる。

### 推奨

- OBS オーバーレイ用途のみなら **方法 B**（パス制限）が最もシンプル
- 外出先からダッシュボードも見たい場合は **方法 A**（Cloudflare Access）を併用

## 8. OBS での使用

OBS のブラウザソースに Tunnel URL を設定:

| 設定項目 | 値 |
|----------|-----|
| URL | `https://sf6.example.com/overlay/record?theme=sf6&size=medium` |
| 幅 | 400 |
| 高さ | 200 |
| カスタム CSS | （不要、テーマパラメータで調整） |

分割オーバーレイ URL（`/overlay/record`, `/overlay/lp`, `/overlay/history`）を個別のブラウザソースとして追加すれば、OBS 上で自由に配置できる。
