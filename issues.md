# SF6 Stats Tracker — Issues / Remaining Tasks

## 改善案  
 - [ ] Twitch BOTとの連携
   - Session Managementの自動作成
   - 配信の開始･終了の取得
   - ※外部依存のため後回し
 - [x] ポップアップ通知について、MRは100毎に通知（MR1600、MR1700、MR1800でそれぞれ◯◯MASTERになる）
   - MR マイルストーンを 100 刻みで動的生成 (上限なし)
   - ラベルに MASTER ティア名表示 (例: "1500 MASTER 到達!")
 - [x] 最高MR更新の通知も表示してほしい
   - config DB に best_mr を永続化、試合毎に比較
   - 更新時に "最高 MR 更新! MR xxxx" ポップアップ表示
   - Popup Notification Settings で ON/OFF 可能