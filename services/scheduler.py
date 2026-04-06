import time
import threading
from apscheduler.schedulers.background import BackgroundScheduler

import config as c
from services import storage, cfn_auth, cfn_scraper

_MAX_BACKOFF = 1800  # 30 minutes

scheduler = BackgroundScheduler(timezone='Asia/Tokyo')

_status = {
    'last_fetch': None,
    'last_error': None,
    'error_count': 0,
    'matches_found': 0,
    'is_running': False,
    'auth_ok': None,       # None=未チェック, True=OK, False=失敗
    'auth_checked_at': None,
    'auto_login_last': None,   # 最後の自動ログイン試行結果
    'consecutive_errors': 0,
    'next_retry_at': None,
}
_status_lock = threading.Lock()


def _try_auto_login():
    """自動ログインを試行。成功なら True、失敗/未設定なら False"""
    try:
        result = cfn_auth.refresh_cookie()
        if result:
            with _status_lock:
                _status['auto_login_last'] = f'success at {c.get_now().isoformat()}'
                _status['auth_ok'] = True
                _status['auth_checked_at'] = c.get_now().isoformat()
            return True
        return False
    except cfn_auth.TwoFactorRequired as e:
        c.log(f'Auto-login blocked: {e}')
        with _status_lock:
            _status['auto_login_last'] = f'2FA required: {e}'
        return False
    except Exception as e:
        c.log(f'Auto-login failed: {e}')
        with _status_lock:
            _status['auto_login_last'] = f'failed: {e}'
        return False


def _poll_job():
    # Backoff guard: skip this invocation if we're still in backoff
    with _status_lock:
        next_retry = _status['next_retry_at']
    if next_retry is not None and time.time() < next_retry:
        return

    mock_mode = storage.get_config('mock_mode', 'true') == 'true'
    try:
        session = cfn_auth.get_session()
        matches = cfn_scraper.fetch_battle_log(session)

        # 新しい順で返ってくるので、古い順に挿入して差分計算を正確にする
        new_matches = [m for m in reversed(matches) if not storage.match_exists(m['replay_id'])]

        new_count = 0
        for match in new_matches:
            _fill_lp_mr_before(match)
            storage.insert_match(match)
            new_count += 1

        now = c.get_now().isoformat()
        with _status_lock:
            _status['last_fetch'] = now
            _status['last_error'] = None
            _status['error_count'] = 0
            _status['consecutive_errors'] = 0
            _status['next_retry_at'] = None
            _status['matches_found'] += new_count
            if not mock_mode:
                _status['auth_ok'] = True
                _status['auth_checked_at'] = now

        if new_count > 0:
            c.log(f'Fetched {new_count} new match(es)')

    except Exception as e:
        error_msg = str(e)
        interval = int(storage.get_config('poll_interval', '90'))
        with _status_lock:
            _status['last_error'] = error_msg
            _status['error_count'] += 1
            _status['consecutive_errors'] += 1
            delay = min(interval * (2 ** _status['consecutive_errors']), _MAX_BACKOFF)
            _status['next_retry_at'] = time.time() + delay
        c.log(f'Poll error: {e}')
        c.log(f'Backing off: next retry in {delay}s')

        # 認証エラーの場合、自動ログインを試行
        if not mock_mode and ('403' in error_msg or 'cookie' in error_msg.lower()):
            c.log('Poll: auth error detected, attempting auto-login...')
            _try_auto_login()


def _check_auth_job():
    """定期的に Cookie の有効性をチェック"""
    mock_mode = storage.get_config('mock_mode', 'true') == 'true'
    if mock_mode:
        return

    cookie = storage.get_config('cfn_cookie')
    if not cookie:
        # Cookie なし → 自動ログインを試行
        if _try_auto_login():
            return
        with _status_lock:
            _status['auth_ok'] = False
            _status['auth_checked_at'] = c.get_now().isoformat()
        return

    session = cfn_auth.get_session()
    build_id = cfn_auth.get_build_id(session, force_refresh=True)
    ok = build_id is not None

    if not ok:
        c.log('Auth check: Cookie may be expired, attempting auto-login...')
        if _try_auto_login():
            return

    with _status_lock:
        _status['auth_ok'] = ok
        _status['auth_checked_at'] = c.get_now().isoformat()


def _fill_lp_mr_before(match):
    """直前のマッチの lp_after/mr_after を lp_before/mr_before に設定"""
    prev = storage.get_matches(limit=1)
    if prev:
        match['lp_before'] = prev[0].get('lp_after')
        match['mr_before'] = prev[0].get('mr_after')


def start_scheduler():
    storage.init_db()
    interval = int(storage.get_config('poll_interval', '90'))
    scheduler.add_job(
        _poll_job, 'interval', seconds=interval,
        id='cfn_poll', replace_existing=True
    )
    # 認証チェック: 10分ごと
    scheduler.add_job(
        _check_auth_job, 'interval', minutes=10,
        id='auth_check', replace_existing=True
    )
    scheduler.start()
    with _status_lock:
        _status['is_running'] = True
    c.log(f'Scheduler started (interval={interval}s)')


def stop_scheduler():
    scheduler.shutdown(wait=False)
    with _status_lock:
        _status['is_running'] = False
    c.log('Scheduler stopped')


def get_scheduler_status():
    with _status_lock:
        status = _status.copy()

    job = scheduler.get_job('cfn_poll')
    status['next_run'] = job.next_run_time.isoformat() if job and job.next_run_time else None

    # Cookie 経過時間を計算
    saved_at = storage.get_config('cfn_cookie_saved_at')
    if saved_at:
        status['cookie_saved_at'] = saved_at
    else:
        status['cookie_saved_at'] = None

    # 自動ログイン設定有無
    email = storage.get_config('capcom_email')
    status['auto_login_configured'] = bool(email)

    return status
