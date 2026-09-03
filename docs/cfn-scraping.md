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
- **ログイン起点**: `https://www.streetfighter.com/6/buckler/ja-jp/auth/loginep?redirect_url=/`
- **フロー**: Buckler `/ja-jp/auth/loginep` → CID (`cid.capcom.com`) → Auth0 (`auth.cid.capcom.com`) → CID callback → Buckler
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

## ポーリング制御

- Settings の poll_interval は通常頻度として扱い、実行時の低速間隔は保存しない。
- 実CFNから正常なレスポンスを取得したものの、新規リプレイIDが5回連続で
  見つからなかった場合は、実行時の取得間隔を300秒へ落とす。
- 新規戦績の検出、Dashboardの「通常頻度に戻す」、またはMock Modeの有効化で
  設定済みの通常頻度へ戻す。
- WAF、429、通信失敗、メンテナンス、レスポンス形式不正は「更新なし」と区別し、
  90秒を下限とする指数バックオフ（最大1800秒）を適用する。
- 「通常頻度に戻す」はアイドル低速化だけを解除し、エラーバックオフは解除しない。
- Dashboardおよび /api/status はキャッシュ済みの認証・スケジューラ状態だけを
  参照し、画面表示を契機にCFNへアクセスしない。

## 直近のエラー履歴

- Settings ページの下部に、直近20件のエラーを
  新しい順に表示する。通常の `Last error` が次の取得成功で消えても、履歴は残る。
- 戦績取得、BuildID 取得、定期認証確認、自動ログイン（通常方式の失敗後に
  代替方式で成功した場合も含む）、ログインテスト、個々の戦績の解析を記録する。
  同じ試行でも異なる処理段階で失敗すると、複数件になることがある。
- 表示項目は日時（JST・秒まで）、発生箇所、分類と定型の説明、例外の種類、
  取得できた場合の HTTP ステータス。例外メッセージやスタックトレース全文、
  通信先 URL・ヘッダー・本文、Cookie、アカウント情報、リプレイ ID は保存しない。
  既存のコンソールログや `Last error` を転載する機能ではない。
- 履歴は起動中のメモリだけに保持する。取得・認証の成功、通常頻度への復帰では
  消えないが、21件目以降は古いものから削除され、アプリ再起動で全件消える。
  導入前や再起動前のエラーは復元できない。
- `/api/status` の `scheduler.recent_errors` でも参照できる。画面は既存の
  10秒ごとの状態取得に合わせて更新し、追加の CFN 通信は発生させない。
- 履歴は過去の出来事であり、現在も失敗中とは限らない。現在の状態は
  Scheduler の Mode / Last fetch / Last error と合わせて確認する。

## 注意事項

- CFN へのリクエスト間隔は **90秒以上** を遵守
- サイト仕様変更で BuildID やレスポンス構造が変わる可能性あり
- `cfn_scraper.py` をモジュール分離してあるため差し替えは容易
- エラー時は exponential backoff でリトライ間隔を延長

## 参考実装

- [cfn-tracker](https://github.com/williamsjokvist/cfn-tracker) (Go) — ブラウザ自動操作で `#__NEXT_DATA__` を取得
- [sfbuff](https://github.com/alanoliveira/sfbuff) (Ruby/Rails) — HTTP リクエストで `_next/data` エンドポイントを直接叩く
- [SF6_Ranking_Data](https://github.com/AJardelH/SF6_Ranking_Data) (Python) — バトルログページの JSON パース
