import os
import threading
from datetime import datetime, timedelta, timezone

DB_PATH = 'data/stats.db'

MAX_LOGS = 50

# JST (日本標準時) の定義
JST = timezone(timedelta(hours=9))

# スレッド安全なリストとロック
logs = []
_log_lock = threading.Lock()

# DB操作用ロック
db_lock = threading.RLock()

DEFAULT_CONFIG = {
    'cfn_cookie': '',
    'cfn_cookie_saved_at': '',
    'cfn_user_id': '',
    'capcom_email': '',
    'capcom_password': '',
    'poll_interval': '90',
    'mock_mode': 'true',
    'overlay_theme': 'dark',
    # ポップアップ通知設定 (1=有効, 0=無効)
    'popup_match_result': '1',
    'popup_lp_mr_delta': '1',
    'popup_rank_change': '1',
    'popup_mr_milestone': '1',
    'popup_streak_record': '1',
    'popup_best_mr': '1',
    # キャラフィルター設定
    'overlay_char_filter': 'off',     # off | auto | manual
    'overlay_char_manual': '',
    # 目標設定
    'goal_type': '',         # mr, lp, winrate, or empty
    'goal_value': '',
    'goal_label': '',
    # セッション自動化
    'session_auto': 'false',
}


def log(message):
    print(message)
    with _log_lock:
        logs.insert(0, {'message': message, 'timestamp': get_now().isoformat()})
        if len(logs) > MAX_LOGS:
            logs.pop()


def get_now():
    return datetime.now(JST)
