import threading
from apscheduler.schedulers.background import BackgroundScheduler

import config as c
from services import storage, cfn_auth, cfn_scraper

scheduler = BackgroundScheduler(timezone='Asia/Tokyo')

_status = {
    'last_fetch': None,
    'last_error': None,
    'error_count': 0,
    'matches_found': 0,
    'is_running': False,
    'auth_ok': None,       # None=未チェック, True=OK, False=失敗
    'auth_checked_at': None,
}
_status_lock = threading.Lock()


def _poll_job():
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
            _status['matches_found'] += new_count
            if not mock_mode:
                _status['auth_ok'] = True
                _status['auth_checked_at'] = now

        if new_count > 0:
            c.log(f'Fetched {new_count} new match(es)')

    except Exception as e:
        with _status_lock:
            _status['last_error'] = str(e)
            _status['error_count'] += 1
        c.log(f'Poll error: {e}')


def _check_auth_job():
    """定期的に Cookie の有効性をチェック"""
    mock_mode = storage.get_config('mock_mode', 'true') == 'true'
    if mock_mode:
        return

    cookie = storage.get_config('cfn_cookie')
    if not cookie:
        with _status_lock:
            _status['auth_ok'] = False
            _status['auth_checked_at'] = c.get_now().isoformat()
        return

    session = cfn_auth.get_session()
    build_id = cfn_auth.get_build_id(session, force_refresh=True)
    ok = build_id is not None

    if not ok:
        c.log('Auth check: Cookie may be expired or invalid')

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
    return status
