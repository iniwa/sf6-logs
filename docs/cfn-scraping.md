# CFN スクレイピング設計メモ

## 調査結果（2026-04-06）

### サイト構造

Buckler's Boot Camp (`https://www.streetfighter.com/6/buckler/`) は **Next.js SSR** で構築されている。
ページ HTML 内の `<script id="__NEXT_DATA__">` にサーバーレンダリングされた JSON データが埋め込まれる。

### API エンドポイント

公式 API は存在しない。Next.js の内部 `_next/data` エンドポイントを利用する。

```
Base: https://www.streetfighter.com
Path: /6/buckler/_next/data/{buildId}/en/{resource}.json
```

| リソース | パス | パラメータ |
|----------|------|-----------|
| バトルログ | `profile/{short_id}/battlelog.json` | `?page=N` (1〜10) |
| プレイプロフィール | `profile/{short_id}/play.json` | — |
| ファイター検索 | `fighterslist/search/result.json` | `?short_id=` or `?fighter_id=` |

### BuildID

- Next.js のビルド毎に変わる識別子
- メインページ (`/6/buckler`) の `#__NEXT_DATA__` JSON 内 `buildId` フィールドから取得
- サイト更新（デプロイ）時に変更されるため、定期的に再取得が必要

### 認証

- **方式**: Cookie ベース
- **ログインフロー**: CAPCOM ID (`cid.capcom.com`) でメール+パスワード認証 → OAuth リダイレクト → Buckler セッション Cookie 発行
- **ログイン URL**: `https://cid.capcom.com/ja/login/?guidedBy=web`
- **コールバック**: `https://www.streetfighter.com/6/buckler/auth/loginep?redirect_url=/`
- **本アプリでの方式**: ユーザーがブラウザ DevTools からコピーした Cookie を Settings 画面に貼り付け

### エラーハンドリング

| HTTP Status | 意味 | 対応 |
|-------------|------|------|
| 200 | 成功 | — |
| 403 | 未認証 / Cookie 無効 | Cookie 再設定を促す |
| 404 (text/html) | ページ / ユーザー不在 | short_id 確認を促す |
| 405 + `x-amzn-waf-action` ヘッダー | AWS WAF レート制限 | exponential backoff |
| 503 | メンテナンス中 | リトライ待機 |

### レスポンス構造（バトルログ）

```json
{
  "pageProps": {
    "fighter_banner_info": {
      "personal_info": { "fighter_id": "...", "short_id": 12345 },
      "favorite_character_id": 1,
      "league_point": 25000,
      "master_rating": 1500
    },
    "replay_list": [
      {
        "replay_id": "XXXXXXXX",
        "replay_battle_type": 1,
        "replay_battle_type_name": "Ranked Match",
        "player1_info": {
          "player": { "fighter_id": "...", "short_id": 12345 },
          "playing_character_name": "Ryu",
          "league_point": 25000,
          "master_rating": 1500,
          "round_results": [1, 1, 0]
        },
        "player2_info": { ... },
        "uploaded_at": 1712345678
      }
    ],
    "current_page": 1,
    "total_page": 5
  }
}
```

### 勝敗判定

`round_results` 配列: `1` = ラウンド勝ち, `0` = ラウンド負け
- `round_results.count(0) >= 2` → マッチ敗北
- `round_results.count(1) >= 2` → マッチ勝利

### プレイヤー識別

- **short_id**: 数値ID（URL で使用、不変）
- **fighter_id**: 表示名（変更可能）

自分が `player1_info` か `player2_info` かは `short_id` で判定する。

## データ契約（mock ↔ real 共通）

`fetch_battle_log()` が返す `list[dict]` の各要素:

```python
{
    'replay_id': str,       # CFNリプレイID（重複排除キー）
    'played_at': str,       # ISO 8601 形式
    'battle_type': str,     # 'ranked' | 'casual' | 'custom'
    'my_character': str,    # キャラクター名
    'opp_character': str,
    'opp_name': str,        # 相手プレイヤー名
    'result': str,          # 'win' | 'lose'
    'lp_before': int | None,
    'lp_after': int | None,
    'mr_before': int | None,
    'mr_after': int | None,
    'raw_data': any | None, # 取得した生データ
}
```

この I/F を変えずにモック → 実装を差し替える設計。

## 実装方針

### Phase 1（現在）: requests + BeautifulSoup

- Playwright **不要** — `#__NEXT_DATA__` は HTML に埋め込まれたサーバーレンダリング JSON
- `_next/data` エンドポイントは直接 JSON を返すため、HTML パース不要
- Cookie はユーザーが手動で Settings 画面に貼り付け
- BuildID はメインページから自動取得

### Phase 2: 自動ログイン（検討中）

- Playwright で CAPCOM ID ログインを自動化
- Cookie 有効期限の監視と自動更新
- ただし Raspberry Pi (ARM64) での Playwright 対応状況に注意

## 注意事項

- CFN へのリクエスト間隔は **90秒以上** を遵守
- サイト仕様変更で BuildID やレスポンス構造が変わる可能性あり
- `cfn_scraper.py` をモジュール分離してあるため差し替えは容易
- エラー時は exponential backoff でリトライ間隔を延長

## 参考実装

- [cfn-tracker](https://github.com/williamsjokvist/cfn-tracker) (Go) — ブラウザ自動操作で `#__NEXT_DATA__` を取得
- [sfbuff](https://github.com/alanoliveira/sfbuff) (Ruby/Rails) — HTTP リクエストで `_next/data` エンドポイントを直接叩く
- [SF6_Ranking_Data](https://github.com/AJardelH/SF6_Ranking_Data) (Python) — バトルログページの JSON パース
