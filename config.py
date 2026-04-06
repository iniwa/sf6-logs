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
}


def log(message):
    print(message)
    with _log_lock:
        logs.insert(0, {'message': message, 'timestamp': get_now().isoformat()})
        if len(logs) > MAX_LOGS:
            logs.pop()


def get_now():
    return datetime.now(JST)
