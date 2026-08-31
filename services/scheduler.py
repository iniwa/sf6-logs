import math
import time
import threading
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

import config as c
from services import storage, cfn_auth, cfn_scraper, error_history

_MAX_BACKOFF = 1800  # 30 minutes
_MIN_ERROR_INTERVAL = 90
_IDLE_EMPTY_THRESHOLD = 5
_IDLE_INTERVAL = 300

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
    'normal_interval': 90,
    'effective_interval': 90,
    'consecutive_empty_fetches': 0,
    'is_idle_slowed': False,
}
_status_lock = threading.Lock()
_poll_schedule_lock = threading.Lock()


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
        error_history.record('auto_login', e, kind='two_factor')
        c.log(f'Auto-login blocked: {e}')
        with _status_lock:
            _status['auto_login_last'] = f'2FA required: {e}'
        return False
    except Exception as e:
        error_history.record('auto_login', e)
        c.log(f'Auto-login failed: {e}', exc_info=True)
        with _status_lock:
            _status['auto_login_last'] = f'failed: {e}'
        return False


def _reschedule_poll_job(seconds):
    """Reschedule the CFN job when it has already been registered."""
    if scheduler.get_job('cfn_poll') is None:
        return False
    scheduler.reschedule_job('cfn_poll', trigger='interval', seconds=seconds)
    return True


def _error_backoff_delay(normal_interval, consecutive_errors, retry_after=None):
    base = max(int(normal_interval), _MIN_ERROR_INTERVAL)
    delay = min(base * (2 ** consecutive_errors), _MAX_BACKOFF)
    if retry_after is not None:
        delay = max(delay, min(int(retry_after), _MAX_BACKOFF))
    return delay


def _record_poll_error(error, mock_mode, expected=False):
    kind = getattr(error, 'kind', 'unexpected')
    status_code = getattr(error, 'status_code', None)
    retry_after = getattr(error, 'retry_after', None)
    error_history.record(
        'poll', error,
        kind=getattr(error, 'kind', None),
        status_code=status_code,
    )
    label = kind if status_code is None else f'{kind}/{status_code}'
    error_msg = f'{label}: {error}'
    normal_interval = int(storage.get_config('poll_interval', '90'))
    now = c.get_now().isoformat()

    with _status_lock:
        _status['last_error'] = error_msg
        _status['error_count'] += 1
        _status['consecutive_errors'] += 1
        delay = _error_backoff_delay(
            normal_interval,
            _status['consecutive_errors'],
            retry_after,
        )
        _status['next_retry_at'] = time.time() + delay
        if kind == 'auth' and not mock_mode:
            _status['auth_ok'] = False
            _status['auth_checked_at'] = now

    c.log(f'Poll error: {error_msg}', exc_info=not expected)
    c.log(f'Backing off: next retry in {delay}s')

    is_auth_error = kind == 'auth' or (
        '403' in str(error) or 'cookie' in str(error).lower()
    )
    if not mock_mode and is_auth_error:
        c.log('Poll: auth error detected, attempting auto-login...')
        _try_auto_login()


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
            _backfill_prev_after(match)
            storage.insert_match(match)
            new_count += 1

        now = c.get_now().isoformat()
        transition_log = None
        with _poll_schedule_lock:
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

                normal_interval = _status['normal_interval']
                if mock_mode:
                    _status['consecutive_empty_fetches'] = 0
                    if (
                        (_status['is_idle_slowed']
                         or _status['effective_interval'] != normal_interval)
                        and _reschedule_poll_job(normal_interval)
                    ):
                        _status['is_idle_slowed'] = False
                        _status['effective_interval'] = normal_interval
                        transition_log = (
                            f'Polling restored to normal interval: '
                            f'{normal_interval}s'
                        )
                elif new_count > 0:
                    _status['consecutive_empty_fetches'] = 0
                    if (
                        (_status['is_idle_slowed']
                         or _status['effective_interval'] != normal_interval)
                        and _reschedule_poll_job(normal_interval)
                    ):
                        _status['is_idle_slowed'] = False
                        _status['effective_interval'] = normal_interval
                        transition_log = (
                            f'Polling restored to normal interval: '
                            f'{normal_interval}s'
                        )
                else:
                    _status['consecutive_empty_fetches'] += 1
                    if (
                        _status['consecutive_empty_fetches']
                        >= _IDLE_EMPTY_THRESHOLD
                        and not _status['is_idle_slowed']
                    ):
                        idle_interval = max(normal_interval, _IDLE_INTERVAL)
                        if (
                            idle_interval > normal_interval
                            and _reschedule_poll_job(idle_interval)
                        ):
                            _status['is_idle_slowed'] = True
                            _status['effective_interval'] = idle_interval
                            transition_log = (
                                f'Polling slowed after '
                                f'{_status["consecutive_empty_fetches"]} empty '
                                f'fetches: {idle_interval}s'
                            )

        if transition_log:
            c.log(transition_log)

        if new_count > 0:
            c.log(f'Fetched {new_count} new match(es)')
            _auto_session_start()

    except cfn_scraper.CfnFetchError as e:
        _record_poll_error(e, mock_mode, expected=True)
    except Exception as e:
        _record_poll_error(e, mock_mode)


def _check_auth_job():
    try:
        return _check_auth_job_impl()
    except Exception as e:
        error_history.record('auth_check', e)
        raise


def _check_auth_job_impl():
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


def _backfill_prev_after(match):
    """DB の直前マッチに after が未設定なら、今回の before で埋める"""
    prev = storage.get_matches(limit=1)
    if not prev:
        return
    prev = prev[0]
    updated = False
    if prev.get('lp_after') is None and match.get('lp_before') is not None:
        prev['lp_after'] = match['lp_before']
        updated = True
    if prev.get('mr_after') is None and match.get('mr_before') is not None:
        prev['mr_after'] = match['mr_before']
        updated = True
    if updated:
        storage.update_match_lp_mr(prev['id'], prev.get('lp_after'), prev.get('mr_after'))


def _auto_session_start():
    """自動セッション: 有効かつアクティブセッションがなければ開始"""
    if storage.get_config('session_auto', 'false') != 'true':
        return
    session = storage.get_current_session()
    if session:
        return
    label = c.get_now().strftime('%Y-%m-%d %H:%M') + ' (auto)'
    storage.start_session(label)
    c.log('Auto session started')


def _auto_session_check():
    """自動セッション: 30分間マッチがなければ終了"""
    if storage.get_config('session_auto', 'false') != 'true':
        return
    session = storage.get_current_session()
    if not session:
        return

    timeout_minutes = 30
    cutoff = c.get_now() - timedelta(minutes=timeout_minutes)
    recent = storage.get_matches_since(cutoff)
    if not recent:
        session_start = datetime.fromisoformat(session['started_at'])
        if session_start.tzinfo is None:
            session_start = session_start.replace(tzinfo=c.JST)
        if c.get_now() - session_start < timedelta(minutes=timeout_minutes):
            return
        storage.end_session(session['id'])
        c.log('Auto session ended (30min inactivity)')


def start_scheduler():
    storage.init_db()
    interval = int(storage.get_config('poll_interval', '90'))
    scheduler.add_job(
        _poll_job, 'interval', seconds=interval,
        id='cfn_poll', replace_existing=True
    )
    with _status_lock:
        _status['normal_interval'] = interval
        _status['effective_interval'] = interval
        _status['consecutive_empty_fetches'] = 0
        _status['is_idle_slowed'] = False
    # 認証チェック: 10分ごと
    scheduler.add_job(
        _check_auth_job, 'interval', minutes=10,
        id='auth_check', replace_existing=True
    )
    # 自動セッションチェック: 5分ごと
    scheduler.add_job(
        _auto_session_check, 'interval', minutes=5,
        id='auto_session_check', replace_existing=True
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


def update_poll_interval(seconds):
    """通常ポーリング間隔を変更し、アイドル低速化を解除する。"""
    seconds = int(seconds)
    with _poll_schedule_lock:
        if not _reschedule_poll_job(seconds):
            c.log('Poll interval update deferred: poll job is not registered')
            return False
        with _status_lock:
            _status['normal_interval'] = seconds
            _status['effective_interval'] = seconds
            _status['consecutive_empty_fetches'] = 0
            _status['is_idle_slowed'] = False
    c.log(f'Poll interval updated: {seconds}s')
    return True


def restore_normal_polling():
    """アイドル低速化だけを解除し、設定済みの通常間隔へ戻す。"""
    interval = int(storage.get_config('poll_interval', '90'))
    with _poll_schedule_lock:
        if not _reschedule_poll_job(interval):
            c.log('Polling restore deferred: poll job is not registered')
            return False
        with _status_lock:
            _status['normal_interval'] = interval
            _status['effective_interval'] = interval
            _status['consecutive_empty_fetches'] = 0
            _status['is_idle_slowed'] = False
    c.log(f'Polling manually restored to normal interval: {interval}s')
    return True


def get_scheduler_status():
    with _poll_schedule_lock:
        with _status_lock:
            status = _status.copy()
        job = scheduler.get_job('cfn_poll')
    status['next_run'] = job.next_run_time.isoformat() if job and job.next_run_time else None

    retry_at = status['next_retry_at']
    status['poll_mode'] = (
        'error' if status['consecutive_errors'] > 0
        else 'idle' if status['is_idle_slowed']
        else 'normal'
    )

    next_attempt_ts = None
    if job and job.next_run_time:
        next_attempt_ts = job.next_run_time.timestamp()
        if retry_at is not None and retry_at > next_attempt_ts:
            interval = max(int(status['effective_interval']), 1)
            skipped_slots = math.ceil(
                (retry_at - next_attempt_ts) / interval
            )
            next_attempt_ts += skipped_slots * interval
    status['next_attempt'] = (
        datetime.fromtimestamp(next_attempt_ts, tz=c.JST).isoformat()
        if next_attempt_ts is not None else None
    )

    # Cookie 経過時間を計算
    saved_at = storage.get_config('cfn_cookie_saved_at')
    if saved_at:
        status['cookie_saved_at'] = saved_at
    else:
        status['cookie_saved_at'] = None

    # 自動ログイン設定有無
    email = storage.get_config('capcom_email')
    status['auto_login_configured'] = bool(email)
    status['recent_errors'] = error_history.get_recent_errors()
    status['recent_errors_limit'] = error_history.MAX_RECENT_ERRORS

    return status
