# CFN スクレイピング設計メモ

## 現状（Phase 1）

`services/cfn_scraper.py` はモック実装。`fetch_battle_log()` がランダムなフェイク対戦データを生成する。
実際の CFN (Buckler's Boot Camp) のページ構造は未調査。

## 実装時の調査事項

1. **ログインフロー**: CAPCOM ID 認証が OAuth / フォームPOST / JS描画のどれか
2. **バトルログページの構造**: HTML 直出し or JavaScript 描画（内部 API 呼び出し）か
3. **Cookie 有効期限**: どの程度持つか → セッション切れ検知ロジックに影響
4. **Playwright の必要性**: JS 描画ページの場合は requests + BeautifulSoup では不可
   - Playwright の ARM64 (Raspberry Pi) 対応状況も確認が必要

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

## 注意事項

- CFN へのリクエスト間隔は **90秒以上** を遵守
- CFN に公式 API は存在しない（スクレイピング）
- サイト仕様変更でパーサーが壊れる可能性 → `cfn_scraper.py` をモジュール分離してある
- エラー時は exponential backoff でリトライ間隔を延長
